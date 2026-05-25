"""
generator.py — 브랜드 데이터를 받아 전체 카드뉴스 세트 생성
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import List, Optional, Tuple

import anthropic
from loguru import logger
from PIL import Image

from config import APIKeys, CardConfig, OUTPUT_DIR
from scrapers.brand_info import BrandOverview
from scrapers.financial_data import FinancialSummary, PLStatement
from scrapers.olive_young import OliveYoungProduct
from scrapers.naver_smartstore import NaverProduct
from scrapers.amazon import AmazonProduct
from scrapers.tiktok import TikTokTrendData
from scrapers.google_trends import TrendSummary
from card_news.card_templates import CardTemplate, CardData
from card_news.waterfall_chart import WaterfallChart


TOTAL_CARDS = 8


class CardNewsGenerator:
    """전체 카드뉴스 8장 세트 생성기"""

    def __init__(self):
        self.template = CardTemplate()
        self.waterfall = WaterfallChart()
        self.ai_client = (
            anthropic.Anthropic(api_key=APIKeys.ANTHROPIC)
            if APIKeys.ANTHROPIC else None
        )

    # ──────────────────────────────────────────────────────────────
    # AI 카피라이팅
    # ──────────────────────────────────────────────────────────────
    def _ai_summary(self, brand_name: str, context: str) -> str:
        """Claude API로 브랜드 요약 생성"""
        if not self.ai_client:
            return f"{brand_name} 브랜드 AI 분석 요약"
        try:
            msg = self.ai_client.messages.create(
                model="claude-opus-4-7",
                max_tokens=400,
                messages=[{
                    "role": "user",
                    "content": (
                        f"다음 {brand_name} 브랜드 데이터를 바탕으로 "
                        f"인스타그램 카드뉴스용 핵심 인사이트를 "
                        f"한국어 3문장으로 요약해주세요. "
                        f"각 문장은 30자 이내로 작성하세요.\n\n{context}"
                    )
                }]
            )
            return msg.content[0].text.strip()
        except Exception as e:
            logger.warning(f"AI 요약 실패: {e}")
            return f"{brand_name} 브랜드 분석 완료"

    # ──────────────────────────────────────────────────────────────
    # 브랜드 컬러 추정
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _pick_brand_color(brand_name: str) -> str:
        """브랜드명 해시 기반 색상 선택"""
        palette = [
            "#E91E8C",  # 핫핑크
            "#00D4FF",  # 사이안
            "#FF6B35",  # 오렌지
            "#7C4DFF",  # 보라
            "#00E676",  # 초록
            "#FFD600",  # 황금
            "#FF1744",  # 레드
            "#00B0FF",  # 스카이블루
        ]
        idx = sum(ord(c) for c in brand_name) % len(palette)
        return palette[idx]

    # ──────────────────────────────────────────────────────────────
    # 카드 1 — 커버
    # ──────────────────────────────────────────────────────────────
    def _card_cover(self, brand: BrandOverview, color: str) -> Image.Image:
        subtitle = ""
        if brand.founded_year:
            subtitle = f"Since {brand.founded_year}"
        if brand.category:
            subtitle += f"  |  {brand.category}"
        return self.template.cover_card(
            brand_name=brand.name,
            subtitle=subtitle,
            tags=brand.tags or [],
            brand_color=color,
            total_cards=TOTAL_CARDS,
        )

    # ──────────────────────────────────────────────────────────────
    # 카드 2 — 브랜드 개요
    # ──────────────────────────────────────────────────────────────
    def _card_overview(self, brand: BrandOverview, color: str) -> Image.Image:
        lines = []
        if brand.founded_year:
            lines.append(f"설립연도: {brand.founded_year}")
        if brand.founder:
            lines.append(f"창업자: {brand.founder}")
        if brand.headquarters:
            lines.append(f"본사: {brand.headquarters}")
        if brand.category:
            lines.append(f"카테고리: {brand.category}")
        if brand.website:
            lines.append(f"웹사이트: {brand.website}")
        if brand.key_products:
            lines.append(f"주요제품: {', '.join(brand.key_products[:3])}")
        # 설명
        if brand.description:
            desc_lines = [brand.description[i:i+30]
                          for i in range(0, min(90, len(brand.description)), 30)]
            lines.extend(desc_lines)

        return self.template.overview_card(CardData(
            card_number=2,
            total_cards=TOTAL_CARDS,
            title=f"🏢  {brand.name} 브랜드 개요",
            subtitle=brand.name_en,
            body_lines=lines,
            brand_color=color,
        ))

    # ──────────────────────────────────────────────────────────────
    # 카드 3 — 전성분
    # ──────────────────────────────────────────────────────────────
    def _card_ingredients(self, brand: BrandOverview, color: str) -> Image.Image:
        ing_names = []
        product_subtitle = ""
        if brand.ingredients:
            first = brand.ingredients[0]
            product_subtitle = f"📦 {first.product_name}"
            ing_names = first.ingredients[:18]
        else:
            ing_names = ["데이터 수집 중"]

        return self.template.ingredients_card(CardData(
            card_number=3,
            total_cards=TOTAL_CARDS,
            title="🧪 핵심 성분 분석",
            subtitle=product_subtitle,
            body_lines=ing_names,
            brand_color=color,
        ))

    # ──────────────────────────────────────────────────────────────
    # 카드 4 — 플랫폼 랭킹
    # ──────────────────────────────────────────────────────────────
    def _card_rankings(
        self,
        brand_name: str,
        oy_products: List[OliveYoungProduct],
        naver_products: List[NaverProduct],
        amazon_products: List[AmazonProduct],
        color: str,
    ) -> Image.Image:
        lines = []

        # 올리브영
        if oy_products:
            for p in oy_products[:2]:
                lines.append(
                    f"🛒 올리브영 #{p.rank} | {p.name[:20]} | {p.price}"
                )
        # 네이버 쇼핑
        if naver_products:
            for p in naver_products[:2]:
                lines.append(
                    f"🟢 네이버 #{p.rank} | {p.name[:20]} | {p.price}"
                )
        # 아마존
        if amazon_products:
            for p in amazon_products[:2]:
                badge = f" 🏆{p.badge}" if p.badge else ""
                lines.append(
                    f"📦 아마존 #{p.rank}{badge} | {p.name[:18]} | {p.price}"
                )
        if not lines:
            lines = ["랭킹 데이터 수집 중..."]

        return self.template.ranking_card(CardData(
            card_number=4,
            total_cards=TOTAL_CARDS,
            title="🏆 플랫폼 랭킹 현황",
            subtitle=f"{brand_name} 주요 플랫폼 순위",
            body_lines=lines,
            brand_color=color,
        ))

    # ──────────────────────────────────────────────────────────────
    # 카드 5 — P&L 워터폴 차트
    # ──────────────────────────────────────────────────────────────
    def _card_pl_waterfall(self, brand_name: str,
                           financial: FinancialSummary,
                           color: str) -> Image.Image:
        chart_img = None
        kpis = []

        if financial.pl_statements:
            latest = financial.pl_statements[0]
            wf_data = latest.to_waterfall()

            try:
                fig = self.waterfall.create(
                    data=wf_data,
                    title=f"{brand_name}  {latest.year}년 손익 구조 (억 원)",
                    subtitle="단위: 억 원",
                    figsize=(9, 5.5),
                )
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=150,
                            bbox_inches="tight", facecolor="#0F0F1A")
                buf.seek(0)
                chart_img = Image.open(buf).copy()
                import matplotlib.pyplot as plt
                plt.close(fig)
            except Exception as e:
                logger.warning(f"워터폴 차트 생성 실패: {e}")

            kpis = [
                f"매출액:{latest.revenue:,.0f}억" if latest.revenue else "",
                f"영업이익률:{latest.operating_margin:.1f}%" if latest.operating_margin else "",
                f"순이익률:{latest.net_margin:.1f}%" if latest.net_margin else "",
                f"EBITDA:{latest.ebitda:,.0f}억" if latest.ebitda else "",
            ]
            kpis = [k for k in kpis if k]

        return self.template.chart_card(CardData(
            card_number=5,
            total_cards=TOTAL_CARDS,
            title="📊 손익 구조 (Waterfall)",
            subtitle=f"최신 연도 P&L · {brand_name}",
            body_lines=kpis,
            chart_image=chart_img,
            brand_color=color,
        ))

    # ──────────────────────────────────────────────────────────────
    # 카드 6 — 투자유치 이력
    # ──────────────────────────────────────────────────────────────
    def _card_investment(self, financial: FinancialSummary,
                         color: str) -> Image.Image:
        lines = []
        for r in financial.investment_rounds[:6]:
            investors_str = ", ".join(r.investors[:2]) if r.investors else ""
            line = f"{r.date} {r.round_type}|{r.amount}"
            if investors_str:
                line += f"|👥 {investors_str}"
            if r.valuation:
                line += f"|기업가치 {r.valuation}"
            lines.append(line)
        if not lines:
            lines = ["투자유치 이력 없음 (비상장)"]

        return self.template.investment_card(CardData(
            card_number=6,
            total_cards=TOTAL_CARDS,
            title="💰 투자유치 이력",
            subtitle="펀딩 라운드 타임라인",
            body_lines=lines,
            brand_color=color,
        ))

    # ──────────────────────────────────────────────────────────────
    # 카드 7 — 트렌드 분석
    # ──────────────────────────────────────────────────────────────
    def _card_trend(self, brand_name: str, tiktok: TikTokTrendData,
                    trends: TrendSummary, color: str) -> Image.Image:
        # 트렌드 수치 (최근 12개월)
        trend_values = [p.value for p in trends.monthly_trend[-12:]] \
                       if trends.monthly_trend else []

        lines = []
        # TikTok 해시태그
        for ht in tiktok.hashtags[:2]:
            lines.append(f"{ht.tag}  {ht.views} views  {ht.trend}")
        # 관련 검색어
        for q in trends.related_queries[:3]:
            lines.append(f"🔍 {q}")

        return self.template.trend_card(
            data=CardData(
                card_number=7,
                total_cards=TOTAL_CARDS,
                title="📈 트렌드 분석",
                subtitle=f"Google Trends 관심도 + TikTok  |  {brand_name}",
                body_lines=lines,
                brand_color=color,
                badge_text=tiktok.virality,
            ),
            trend_values=trend_values,
        )

    # ──────────────────────────────────────────────────────────────
    # 카드 8 — 종합 요약
    # ──────────────────────────────────────────────────────────────
    def _card_summary(self, brand: BrandOverview,
                      financial: FinancialSummary,
                      trends: TrendSummary,
                      tiktok: TikTokTrendData,
                      color: str) -> Image.Image:
        pl = financial.pl_statements[0] if financial.pl_statements else None
        scores = []
        if pl and pl.operating_margin:
            scores.append(f"영업이익률|{pl.operating_margin:.1f}%")
        if trends.interest_score:
            scores.append(f"트렌드지수|{trends.interest_score}/100")
        if tiktok.hashtags:
            scores.append(f"TikTok|{tiktok.hashtags[0].views}")

        context = (
            f"매출 {pl.revenue}억 | 영업이익 {pl.operating_income}억 | "
            f"트렌드지수 {trends.interest_score}"
            if pl else brand.description
        )
        ai_text = self._ai_summary(brand.name, context)
        ai_lines = [l.strip() for l in ai_text.split("\n") if l.strip()][:3]

        lines = scores + ["─" * 20] + ai_lines + [
            f"📌 투자 {len(financial.investment_rounds)}라운드 완료",
            f"🛒 {len(financial.investment_rounds)}개 플랫폼 입점",
        ]

        return self.template.summary_card(CardData(
            card_number=8,
            total_cards=TOTAL_CARDS,
            title="✅ 종합 분석 요약",
            subtitle=f"AI 인사이트  |  {brand.name}",
            body_lines=lines,
            highlight_box="📲 팔로우하고 다음 리포트도 받아보세요!",
            brand_color=color,
        ))

    # ──────────────────────────────────────────────────────────────
    # 공개 인터페이스
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
        """8장 카드뉴스 이미지 파일 생성"""
        out_dir = output_dir or (OUTPUT_DIR / brand.name.replace(" ", "_"))
        out_dir.mkdir(parents=True, exist_ok=True)
        color = self._pick_brand_color(brand.name)

        logger.info(f"[Generator] '{brand.name}' 카드뉴스 생성 시작 (color={color})")

        cards: List[Tuple[str, Image.Image]] = [
            ("01_cover",       self._card_cover(brand, color)),
            ("02_overview",    self._card_overview(brand, color)),
            ("03_ingredients", self._card_ingredients(brand, color)),
            ("04_rankings",    self._card_rankings(brand.name, oy_products,
                                                    naver_products, amazon_products,
                                                    color)),
            ("05_pl_waterfall",self._card_pl_waterfall(brand.name, financial, color)),
            ("06_investment",  self._card_investment(financial, color)),
            ("07_trend",       self._card_trend(brand.name, tiktok, trends, color)),
            ("08_summary",     self._card_summary(brand, financial, trends, tiktok, color)),
        ]

        paths: List[Path] = []
        for fname, img in cards:
            path = out_dir / f"{fname}.png"
            img.save(str(path), "PNG", optimize=True)
            logger.success(f"  ✓ {path.name}")
            paths.append(path)

        logger.success(f"[Generator] 카드뉴스 {len(paths)}장 생성 완료 → {out_dir}")
        return paths
