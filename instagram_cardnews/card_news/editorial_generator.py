"""
editorial_generator.py — 화이트 에디토리얼 카드뉴스 8장 생성 (신규 기본)
  • kodeok.kr 톤&매너 + ekke.now Sankey 손익도
  • AI 카피라이팅(EditorialCopywriter) + 카드별 사진 임베딩
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger
from PIL import Image

from config import OUTPUT_DIR, EditorialTheme as ET
from scrapers.brand_info import BrandOverview
from scrapers.financial_data import FinancialSummary
from scrapers.olive_young import OliveYoungProduct
from scrapers.naver_smartstore import NaverProduct
from scrapers.amazon import AmazonProduct
from scrapers.tiktok import TikTokTrendData
from scrapers.google_trends import TrendSummary

from card_news.editorial_templates import EditorialCard
from card_news.sankey_chart import SankeyPLChart
from prompts.copywriting import EditorialCopywriter
from utils.image_fetch import download_first_valid

TOTAL = 8

_PALETTE = [
    "#E2452A", "#2563EB", "#16A34A", "#7C3AED",
    "#DB2777", "#EA580C", "#0891B2", "#CA8A04",
]


class EditorialCardNewsGenerator:
    def __init__(self):
        self.card = EditorialCard()
        self.sankey = SankeyPLChart()
        self.writer = EditorialCopywriter()

    @staticmethod
    def _accent(brand: str) -> str:
        return _PALETTE[sum(ord(c) for c in brand) % len(_PALETTE)]

    # ──────────────────────────────────────────────────────────────
    # 사진 수집 헬퍼 — 스크래핑 URL → 다운로드 (실패 시 None → 플레이스홀더)
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _collect_product_photos(
        brand: BrandOverview,
        naver: List[NaverProduct],
        oy: List[OliveYoungProduct],
        amazon: List[AmazonProduct],
        n: int = 3,
    ) -> Tuple[List[Optional[Image.Image]], List[str]]:
        url_label: List[Tuple[str, str]] = []
        for p in naver:
            if p.image:
                url_label.append((p.image, p.name[:10]))
        for p in oy:
            if p.image_url:
                url_label.append((p.image_url, p.name[:10]))
        for p in amazon:
            if p.image:
                url_label.append((p.image, p.brand[:10]))
        if brand.logo_url:
            url_label.insert(0, (brand.logo_url, brand.name[:10]))

        photos: List[Optional[Image.Image]] = []
        labels: List[str] = []
        for url, lbl in url_label[:n]:
            photos.append(download_first_valid([url]))
            labels.append(lbl)
        # 부족분 채우기 (플레이스홀더용 None + 라벨)
        defaults = (brand.key_products or [])[:n]
        while len(photos) < n:
            photos.append(None)
            idx = len(labels)
            labels.append(defaults[idx] if idx < len(defaults) else brand.name)
        return photos, labels

    # ──────────────────────────────────────────────────────────────
    def generate(
        self,
        brand: BrandOverview,
        financial: FinancialSummary,
        oy_products: List[OliveYoungProduct],
        naver_products: List[NaverProduct],
        amazon_products: List[AmazonProduct],
        tiktok: TikTokTrendData,
        trends: TrendSummary,
        output_dir: Optional[Path] = None,
    ) -> List[Path]:
        out = output_dir or (OUTPUT_DIR / f"{brand.name.replace(' ', '_')}_editorial")
        out.mkdir(parents=True, exist_ok=True)
        accent = self._accent(brand.name)
        logger.info(f"[Editorial] '{brand.name}' 생성 시작 (accent={accent})")

        pl = financial.pl_statements[0] if financial.pl_statements else None

        # 사진 수집
        photos, labels = self._collect_product_photos(
            brand, naver_products, oy_products, amazon_products, n=3)
        hero = next((p for p in photos if p is not None), None)

        # ── 카드별 AI 카피 ──────────────────────────────────────
        cover_copy = self.writer.write("cover", brand.name, {
            "category": brand.category, "tags": brand.tags,
        })
        overview_copy = self.writer.write("overview", brand.name, {
            "founded_year": brand.founded_year, "founder": brand.founder,
            "category": brand.category, "headquarters": brand.headquarters,
            "key_products": brand.key_products, "description": brand.description,
        })
        ing_names = (brand.ingredients[0].ingredients[:6]
                     if brand.ingredients else [])
        ing_copy = self.writer.write("ingredients", brand.name, {
            "product": brand.ingredients[0].product_name if brand.ingredients else "",
            "ingredients": ing_names,
        })
        top_rank = "#1"
        if oy_products:
            top_rank = f"#{min(p.rank for p in oy_products)}"
        rank_copy = self.writer.write("ranking", brand.name, {
            "oliveyoung": [(p.rank, p.name) for p in oy_products[:3]],
            "naver": [(p.rank, p.name) for p in naver_products[:3]],
            "amazon": [(p.rank, p.name, p.badge) for p in amazon_products[:3]],
            "top_rank": top_rank,
        })
        pl_copy = self.writer.write("pl", brand.name, {
            "revenue": pl.revenue if pl else "",
            "operating_margin": pl.operating_margin if pl else "",
            "net_margin": pl.net_margin if pl else "",
        } if pl else {})
        total_funding = ", ".join(r.amount for r in financial.investment_rounds[:1])
        last_val = (financial.investment_rounds[-1].valuation
                    if financial.investment_rounds else "")
        inv_copy = self.writer.write("investment", brand.name, {
            "rounds": [(r.date, r.round_type, r.amount, r.valuation)
                       for r in financial.investment_rounds],
            "total_funding": total_funding, "valuation": last_val,
        })
        trend_copy = self.writer.write("trend", brand.name, {
            "trend_score": trends.interest_score,
            "tiktok_views": tiktok.hashtags[0].views if tiktok.hashtags else "",
            "related": trends.related_queries,
            "virality": tiktok.virality,
        })
        sum_copy = self.writer.write("summary", brand.name, {
            "operating_margin": pl.operating_margin if pl else "",
            "trend_score": trends.interest_score,
            "rounds": len(financial.investment_rounds),
        })

        # ── Sankey 차트 ─────────────────────────────────────────
        chart_img = None
        kpis = []
        if pl:
            try:
                chart_img = self.sankey.create(pl, brand.name)
            except Exception as e:
                logger.warning(f"Sankey 생성 실패: {e}")
            kpis = [k for k in [
                f"매출:{pl.revenue:,.0f}억" if pl.revenue else "",
                f"영업이익률:{pl.operating_margin:.1f}%" if pl.operating_margin else "",
                f"순이익률:{pl.net_margin:.1f}%" if pl.net_margin else "",
                f"매출총이익률:{pl.gross_margin:.1f}%" if pl.gross_margin else "",
            ] if k]

        # 투자 카드 콜아웃에 타임라인 주입
        if financial.investment_rounds and not inv_copy.callout:
            inv_copy.callout = [
                f"{r.date}  {r.round_type}  {r.amount}"
                for r in financial.investment_rounds[:4]
            ]
        # 트렌드 카드 콜아웃에 검색어
        if trends.related_queries and not trend_copy.callout:
            trend_copy.callout = ["연관 검색어"] + [
                f"→ {q}" for q in trends.related_queries[:3]]

        # ── 카드 빌드 ────────────────────────────────────────────
        cards: List[Tuple[str, Image.Image]] = [
            ("01_cover",       self.card.cover(brand.name, cover_copy, hero, accent, TOTAL)),
            ("02_overview",    self.card.standard(brand.name, overview_copy, 2, TOTAL,
                                                  accent, photos=[hero], photo_labels=[brand.name],
                                                  photo_band_h=300)),
            ("03_ingredients", self.card.standard(brand.name, ing_copy, 3, TOTAL,
                                                  accent, photos=photos, photo_labels=labels,
                                                  photo_band_h=300)),
            ("04_ranking",     self.card.standard(brand.name, rank_copy, 4, TOTAL,
                                                  accent, photos=photos, photo_labels=labels,
                                                  photo_band_h=300)),
            ("05_pl_sankey",   self.card.pl_chart(brand.name, pl_copy, 5, TOTAL,
                                                  accent, chart_img, kpis)),
            ("06_investment",  self.card.standard(brand.name, inv_copy, 6, TOTAL, accent)),
            ("07_trend",       self.card.standard(brand.name, trend_copy, 7, TOTAL,
                                                  accent, photos=photos, photo_labels=labels,
                                                  photo_band_h=280)),
            ("08_summary",     self.card.standard(brand.name, sum_copy, 8, TOTAL, accent)),
        ]

        paths: List[Path] = []
        for fname, im in cards:
            p = out / f"{fname}.png"
            im.save(str(p), "PNG", optimize=True)
            logger.success(f"  ✓ {p.name}")
            paths.append(p)

        logger.success(f"[Editorial] {len(paths)}장 생성 완료 → {out}")
        return paths
