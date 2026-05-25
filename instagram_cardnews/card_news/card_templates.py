"""
card_templates.py — Instagram 카드뉴스 이미지 템플릿 (Pillow 기반)
  1080×1080px 다크 테마 / 한글 지원
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from loguru import logger

from config import CardConfig, FONTS_DIR
from utils.image_utils import (
    load_korean_font,
    draw_gradient_background,
    draw_rounded_rect,
    draw_glow_text,
    hex_to_rgb,
    paste_image_round,
)

W = CardConfig.WIDTH
H = CardConfig.HEIGHT


@dataclass
class CardData:
    card_number:  int
    total_cards:  int
    title:        str
    subtitle:     str = ""
    body_lines:   List[str] = None     # type: ignore
    highlight_box: str = ""            # 하이라이트 박스 텍스트
    badge_text:    str = ""            # 우측 상단 뱃지
    chart_image:  Optional[Image.Image] = None
    brand_color:  str = "#E91E8C"


class CardTemplate:
    """카드뉴스 이미지 생성기"""

    def __init__(self):
        self.fonts = self._load_fonts()

    def _load_fonts(self) -> dict:
        fonts = {}
        for size_name, size in [
            ("title_xl", 52), ("title_l", 40), ("title_m", 32),
            ("body_l",   24), ("body_m",   20), ("body_s",   16),
            ("caption",  13), ("badge",    18),
        ]:
            fonts[size_name] = load_korean_font(size)
        return fonts

    # ──────────────────────────────────────────────────────────────
    # 공통 베이스 레이어
    # ──────────────────────────────────────────────────────────────
    def _base_canvas(self, brand_color: str = CardConfig.ACCENT) -> Image.Image:
        img = Image.new("RGB", (W, H), hex_to_rgb(CardConfig.BG_COLOR_START))
        draw_gradient_background(img, CardConfig.BG_COLOR_START,
                                 CardConfig.BG_COLOR_END)

        # 좌측 세로 악센트 바
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 6, H], fill=hex_to_rgb(brand_color))

        # 우측 하단 장식 원
        for r, alpha in [(260, 18), (180, 30), (100, 50)]:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            color = hex_to_rgb(brand_color) + (alpha,)
            od.ellipse([W - r, H - r, W + r, H + r], outline=color, width=2)
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        return img

    def _draw_header(self, img: Image.Image, draw: ImageDraw.ImageDraw,
                     brand_color: str, card_num: int, total: int):
        """카드 번호 + 진행 바"""
        # 진행 바
        bar_w = W - 80
        draw.rectangle([40, 20, 40 + bar_w, 24],
                       fill=hex_to_rgb("#2A2A3E"))
        filled = int(bar_w * card_num / total)
        draw.rectangle([40, 20, 40 + filled, 24],
                       fill=hex_to_rgb(brand_color))
        # 페이지 표시
        page_txt = f"{card_num} / {total}"
        f = self.fonts["caption"]
        draw.text((W - 60, 32), page_txt, fill=hex_to_rgb("#B0BEC5"), font=f,
                  anchor="mt")

    def _draw_footer(self, img: Image.Image, draw: ImageDraw.ImageDraw,
                     brand_name: str, brand_color: str):
        """하단 브랜드 로고 바"""
        draw.rectangle([0, H - 50, W, H], fill=hex_to_rgb("#0A0A14"))
        draw.rectangle([0, H - 52, W, H - 48],
                       fill=hex_to_rgb(brand_color))
        f = self.fonts["caption"]
        draw.text((W // 2, H - 25), f"© {brand_name} 브랜드 분석 리포트",
                  fill=hex_to_rgb("#B0BEC5"), font=f, anchor="mm")

    # ──────────────────────────────────────────────────────────────
    # 카드 1 — 브랜드 커버
    # ──────────────────────────────────────────────────────────────
    def cover_card(self, brand_name: str, subtitle: str = "",
                   tags: List[str] = None,
                   brand_color: str = CardConfig.ACCENT,
                   total_cards: int = 8) -> Image.Image:
        img  = self._base_canvas(brand_color)
        draw = ImageDraw.Draw(img)

        # 중앙 글로우 원형
        for r, a in [(350, 8), (250, 15), (150, 25)]:
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            c  = hex_to_rgb(brand_color)
            cx, cy = W // 2, H // 2 - 60
            od.ellipse([cx - r, cy - r, cx + r, cy + r],
                       fill=c + (a,))
            img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        draw = ImageDraw.Draw(img)

        # 브랜드명
        draw_glow_text(draw, (W // 2, H // 2 - 80), brand_name,
                       self.fonts["title_xl"], brand_color, anchor="mm")

        # 부제목
        if subtitle:
            draw.text((W // 2, H // 2 + 20), subtitle,
                      fill=hex_to_rgb("#FFFFFF"), font=self.fonts["body_l"],
                      anchor="mm")

        # 태그 칩
        if tags:
            chip_x = 60
            chip_y = H // 2 + 90
            for tag in tags[:5]:
                tw, _ = self.fonts["body_s"].getbbox(f"  #{tag}  ")[2:4]
                draw_rounded_rect(draw, (chip_x, chip_y, chip_x + tw + 20,
                                         chip_y + 32),
                                  radius=16, fill=hex_to_rgb(brand_color) + (60,),
                                  outline=hex_to_rgb(brand_color), width=1)
                draw.text((chip_x + (tw + 20) // 2, chip_y + 16),
                          f"#{tag}", fill=hex_to_rgb("#FFFFFF"),
                          font=self.fonts["body_s"], anchor="mm")
                chip_x += tw + 30

        # 카드 번호
        self._draw_header(img, draw, brand_color, 1, total_cards)
        self._draw_footer(img, draw, brand_name, brand_color)

        # 하단 화살표 힌트
        draw.text((W // 2, H - 80), "▶ 스와이프",
                  fill=hex_to_rgb("#555577"), font=self.fonts["caption"],
                  anchor="mm")
        return img

    # ──────────────────────────────────────────────────────────────
    # 카드 2 — 브랜드 개요
    # ──────────────────────────────────────────────────────────────
    def overview_card(self, data: CardData) -> Image.Image:
        img  = self._base_canvas(data.brand_color)
        draw = ImageDraw.Draw(img)
        self._draw_header(img, draw, data.brand_color, data.card_number, data.total_cards)

        # 제목 영역
        draw.text((W // 2, 90), data.title,
                  fill=hex_to_rgb("#FFFFFF"), font=self.fonts["title_l"],
                  anchor="mm")
        draw.rectangle([60, 115, W - 60, 118],
                       fill=hex_to_rgb(data.brand_color))

        # 정보 항목들 (아이콘 + 텍스트)
        y = 160
        for line in (data.body_lines or []):
            if ":" in line:
                label, val = line.split(":", 1)
                draw.text((80, y), f"▪ {label.strip()}",
                          fill=hex_to_rgb("#B0BEC5"), font=self.fonts["body_s"])
                draw.text((320, y), val.strip(),
                          fill=hex_to_rgb("#FFFFFF"), font=self.fonts["body_m"])
            else:
                draw.text((80, y), line,
                          fill=hex_to_rgb("#FFFFFF"), font=self.fonts["body_m"])
            y += 48

        # 하이라이트 박스
        if data.highlight_box:
            box_y = H - 250
            draw_rounded_rect(draw, (60, box_y, W - 60, box_y + 140),
                              radius=16,
                              fill=hex_to_rgb(data.brand_color) + (30,),
                              outline=hex_to_rgb(data.brand_color), width=2)
            draw.text((W // 2, box_y + 70), data.highlight_box,
                      fill=hex_to_rgb("#FFFFFF"), font=self.fonts["body_m"],
                      anchor="mm")

        self._draw_footer(img, draw, "", data.brand_color)
        return img

    # ──────────────────────────────────────────────────────────────
    # 카드 3 — 전성분 카드
    # ──────────────────────────────────────────────────────────────
    def ingredients_card(self, data: CardData) -> Image.Image:
        img  = self._base_canvas(data.brand_color)
        draw = ImageDraw.Draw(img)
        self._draw_header(img, draw, data.brand_color, data.card_number, data.total_cards)

        draw.text((W // 2, 90), data.title,
                  fill=hex_to_rgb("#FFFFFF"), font=self.fonts["title_m"],
                  anchor="mm")
        draw.rectangle([80, 115, W - 80, 118],
                       fill=hex_to_rgb(data.brand_color))

        if data.subtitle:
            draw.text((W // 2, 140), data.subtitle,
                      fill=hex_to_rgb("#B0BEC5"), font=self.fonts["body_s"],
                      anchor="mm")

        # 성분 태그 클라우드
        x, y = 60, 175
        max_per_row = 3
        col = 0
        for ing in (data.body_lines or [])[:18]:
            chip_w = min(290, max(120, len(ing) * 12))
            if x + chip_w > W - 60:
                x  = 60
                y += 52
            # 색상 결정 (주요 성분 강조)
            good_ings = {"나이아신아마이드", "히알루론산", "레티놀", "세라마이드",
                         "판테놀", "비타민C", "펩타이드", "EGF", "콜라겐"}
            is_good = any(g in ing for g in good_ings)
            chip_fill = hex_to_rgb(data.brand_color) + (50,) if is_good \
                        else hex_to_rgb("#1E1E30") + (200,)
            chip_border = hex_to_rgb(data.brand_color) if is_good \
                          else hex_to_rgb("#2A2A3E")
            draw_rounded_rect(draw,
                              (x, y, x + chip_w, y + 36),
                              radius=18, fill=chip_fill,
                              outline=chip_border, width=1)
            draw.text((x + chip_w // 2, y + 18), ing[:20],
                      fill=hex_to_rgb("#FFFFFF" if is_good else "#B0BEC5"),
                      font=self.fonts["caption"], anchor="mm")
            x  += chip_w + 10
            col += 1

        self._draw_footer(img, draw, "", data.brand_color)
        return img

    # ──────────────────────────────────────────────────────────────
    # 카드 4 — 플랫폼 랭킹
    # ──────────────────────────────────────────────────────────────
    def ranking_card(self, data: CardData) -> Image.Image:
        img  = self._base_canvas(data.brand_color)
        draw = ImageDraw.Draw(img)
        self._draw_header(img, draw, data.brand_color, data.card_number, data.total_cards)

        draw.text((W // 2, 90), data.title,
                  fill=hex_to_rgb("#FFFFFF"), font=self.fonts["title_m"],
                  anchor="mm")
        draw.rectangle([80, 115, W - 80, 118],
                       fill=hex_to_rgb(data.brand_color))

        y = 150
        rank_colors = ["#FFD700", "#C0C0C0", "#CD7F32"]
        for i, line in enumerate((data.body_lines or [])[:8]):
            # 교대 배경
            row_bg = hex_to_rgb("#1A1A2E") if i % 2 == 0 else hex_to_rgb("#0F0F1A")
            draw.rectangle([40, y, W - 40, y + 70], fill=row_bg)

            # 랭킹 번호
            rank_color = rank_colors[i] if i < 3 else "#B0BEC5"
            rank_font  = self.fonts["title_m"] if i < 3 else self.fonts["body_l"]
            draw.text((90, y + 35), f"#{i+1}", fill=hex_to_rgb(rank_color),
                      font=rank_font, anchor="mm")

            # 구분선
            draw.rectangle([120, y + 15, 122, y + 55],
                           fill=hex_to_rgb("#2A2A3E"))

            # 내용
            if "|" in line:
                parts = line.split("|")
                draw.text((145, y + 22), parts[0].strip()[:28],
                          fill=hex_to_rgb("#FFFFFF"), font=self.fonts["body_m"])
                if len(parts) > 1:
                    draw.text((145, y + 46), parts[1].strip()[:32],
                              fill=hex_to_rgb("#B0BEC5"), font=self.fonts["body_s"])
            else:
                draw.text((145, y + 35), line[:35],
                          fill=hex_to_rgb("#FFFFFF"), font=self.fonts["body_m"],
                          anchor="lm")
            y += 72

        self._draw_footer(img, draw, "", data.brand_color)
        return img

    # ──────────────────────────────────────────────────────────────
    # 카드 5 — 워터폴 차트 카드
    # ──────────────────────────────────────────────────────────────
    def chart_card(self, data: CardData) -> Image.Image:
        img  = self._base_canvas(data.brand_color)
        draw = ImageDraw.Draw(img)
        self._draw_header(img, draw, data.brand_color, data.card_number, data.total_cards)

        draw.text((W // 2, 75), data.title,
                  fill=hex_to_rgb("#FFFFFF"), font=self.fonts["title_m"],
                  anchor="mm")
        if data.subtitle:
            draw.text((W // 2, 115), data.subtitle,
                      fill=hex_to_rgb("#B0BEC5"), font=self.fonts["body_s"],
                      anchor="mm")
        draw.rectangle([80, 133, W - 80, 136],
                       fill=hex_to_rgb(data.brand_color))

        # 차트 이미지 삽입
        if data.chart_image:
            chart = data.chart_image.resize((W - 80, 580), Image.LANCZOS)
            img.paste(chart, (40, 150))
        else:
            draw.text((W // 2, H // 2), "차트 로딩 중...",
                      fill=hex_to_rgb("#555577"), font=self.fonts["body_l"],
                      anchor="mm")

        # KPI 하단 바
        kpis = data.body_lines or []
        if kpis:
            kpi_y = H - 150
            draw.rectangle([0, kpi_y - 10, W, kpi_y - 8],
                           fill=hex_to_rgb("#2A2A3E"))
            col_w = W // max(len(kpis), 1)
            for i, kpi in enumerate(kpis[:4]):
                cx = i * col_w + col_w // 2
                if ":" in kpi:
                    k, v = kpi.split(":", 1)
                    draw.text((cx, kpi_y + 10), v.strip(),
                              fill=hex_to_rgb(data.brand_color),
                              font=self.fonts["body_l"], anchor="mt")
                    draw.text((cx, kpi_y + 48), k.strip(),
                              fill=hex_to_rgb("#B0BEC5"),
                              font=self.fonts["caption"], anchor="mt")
                else:
                    draw.text((cx, kpi_y + 20), kpi,
                              fill=hex_to_rgb("#FFFFFF"),
                              font=self.fonts["body_m"], anchor="mt")

        self._draw_footer(img, draw, "", data.brand_color)
        return img

    # ──────────────────────────────────────────────────────────────
    # 카드 6 — 투자 이력 타임라인
    # ──────────────────────────────────────────────────────────────
    def investment_card(self, data: CardData) -> Image.Image:
        img  = self._base_canvas(data.brand_color)
        draw = ImageDraw.Draw(img)
        self._draw_header(img, draw, data.brand_color, data.card_number, data.total_cards)

        draw.text((W // 2, 90), data.title,
                  fill=hex_to_rgb("#FFFFFF"), font=self.fonts["title_m"],
                  anchor="mm")
        draw.rectangle([80, 115, W - 80, 118],
                       fill=hex_to_rgb(data.brand_color))

        # 타임라인 수직선
        line_x = 160
        draw.rectangle([line_x - 2, 145, line_x + 2, H - 100],
                       fill=hex_to_rgb("#2A2A3E"))

        y = 155
        for i, line in enumerate((data.body_lines or [])[:6]):
            # 타임라인 노드
            r = 12
            draw.ellipse([line_x - r, y - r, line_x + r, y + r],
                         fill=hex_to_rgb(data.brand_color))
            draw.ellipse([line_x - r + 4, y - r + 4,
                          line_x + r - 4, y + r - 4],
                         fill=hex_to_rgb("#0F0F1A"))

            # 내용
            if "|" in line:
                parts = line.split("|")
                draw.text((line_x + 30, y - 14), parts[0].strip(),
                          fill=hex_to_rgb("#FFFFFF"), font=self.fonts["body_m"])
                for j, p in enumerate(parts[1:], 1):
                    draw.text((line_x + 30, y + 12 + (j - 1) * 22),
                              p.strip(),
                              fill=hex_to_rgb("#B0BEC5"),
                              font=self.fonts["body_s"])
            else:
                draw.text((line_x + 30, y - 10), line,
                          fill=hex_to_rgb("#FFFFFF"), font=self.fonts["body_m"])

            y += 115

        self._draw_footer(img, draw, "", data.brand_color)
        return img

    # ──────────────────────────────────────────────────────────────
    # 카드 7 — 트렌드 분석
    # ──────────────────────────────────────────────────────────────
    def trend_card(self, data: CardData,
                   trend_values: List[int] = None) -> Image.Image:
        img  = self._base_canvas(data.brand_color)
        draw = ImageDraw.Draw(img)
        self._draw_header(img, draw, data.brand_color, data.card_number, data.total_cards)

        draw.text((W // 2, 90), data.title,
                  fill=hex_to_rgb("#FFFFFF"), font=self.fonts["title_m"],
                  anchor="mm")
        draw.rectangle([80, 115, W - 80, 118],
                       fill=hex_to_rgb(data.brand_color))

        # 미니 라인 차트
        if trend_values:
            chart_x1, chart_y1 = 60, 150
            chart_x2, chart_y2 = W - 60, 480
            cw = chart_x2 - chart_x1
            ch = chart_y2 - chart_y1

            draw.rectangle([chart_x1 - 2, chart_y1 - 2,
                            chart_x2 + 2, chart_y2 + 2],
                           fill=hex_to_rgb("#0A0A14"),
                           outline=hex_to_rgb("#2A2A3E"), width=1)

            n   = len(trend_values)
            min_v, max_v = min(trend_values), max(trend_values)
            rng  = max(max_v - min_v, 1)
            pts  = []
            for i, v in enumerate(trend_values):
                px = chart_x1 + int(i / (n - 1) * cw) if n > 1 else chart_x1 + cw // 2
                py = chart_y2 - int((v - min_v) / rng * ch * 0.9) - int(ch * 0.05)
                pts.append((px, py))

            # 그라디언트 채우기 근사
            for j in range(len(pts) - 1):
                x0, y0 = pts[j]
                x1, y1 = pts[j + 1]
                for alpha_step in range(10):
                    a = 5 + alpha_step * 3
                    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    od = ImageDraw.Draw(ov)
                    od.polygon([x0, y0 + alpha_step,
                                x1, y1 + alpha_step,
                                x1, chart_y2,
                                x0, chart_y2],
                               fill=hex_to_rgb(data.brand_color) + (a,))
                    img = Image.alpha_composite(
                        img.convert("RGBA"), ov).convert("RGB")
                draw = ImageDraw.Draw(img)

            # 라인 그리기
            for j in range(len(pts) - 1):
                draw.line([pts[j], pts[j + 1]],
                          fill=hex_to_rgb(data.brand_color), width=3)
            # 현재 포인트
            if pts:
                px, py = pts[-1]
                draw.ellipse([px - 6, py - 6, px + 6, py + 6],
                             fill=hex_to_rgb(data.brand_color))
                draw.text((px, py - 20), f"{trend_values[-1]}",
                          fill=hex_to_rgb("#FFFFFF"),
                          font=self.fonts["body_s"], anchor="mm")

        # 하단 관련 쿼리
        y = 510
        for line in (data.body_lines or [])[:4]:
            draw.text((80, y), f"🔍  {line}",
                      fill=hex_to_rgb("#B0BEC5"), font=self.fonts["body_s"])
            y += 38

        self._draw_footer(img, draw, "", data.brand_color)
        return img

    # ──────────────────────────────────────────────────────────────
    # 카드 8 — 종합 요약
    # ──────────────────────────────────────────────────────────────
    def summary_card(self, data: CardData) -> Image.Image:
        img  = self._base_canvas(data.brand_color)
        draw = ImageDraw.Draw(img)
        self._draw_header(img, draw, data.brand_color, data.card_number, data.total_cards)

        draw.text((W // 2, 90), data.title,
                  fill=hex_to_rgb("#FFFFFF"), font=self.fonts["title_m"],
                  anchor="mm")
        draw.rectangle([80, 115, W - 80, 118],
                       fill=hex_to_rgb(data.brand_color))

        # 점수카드 3개
        scores = (data.body_lines or [])[:3]
        sw = (W - 120) // 3
        for i, item in enumerate(scores):
            sx = 60 + i * (sw + 20)
            draw_rounded_rect(draw,
                              (sx, 145, sx + sw, 310),
                              radius=16,
                              fill=hex_to_rgb("#1A1A2E"),
                              outline=hex_to_rgb(data.brand_color), width=2)
            if "|" in item:
                k, v = item.split("|", 1)
                draw.text((sx + sw // 2, 200), v.strip(),
                          fill=hex_to_rgb(data.brand_color),
                          font=self.fonts["title_m"], anchor="mm")
                draw.text((sx + sw // 2, 258), k.strip(),
                          fill=hex_to_rgb("#B0BEC5"),
                          font=self.fonts["body_s"], anchor="mm")

        # 텍스트 요약
        y = 340
        for line in (data.body_lines or [])[3:8]:
            draw.text((W // 2, y), line,
                      fill=hex_to_rgb("#FFFFFF"), font=self.fonts["body_m"],
                      anchor="mm")
            y += 50

        # 하이라이트 CTA
        if data.highlight_box:
            draw_rounded_rect(draw, (60, H - 220, W - 60, H - 100),
                              radius=20,
                              fill=hex_to_rgb(data.brand_color) + (200,),
                              outline=None)
            draw.text((W // 2, H - 160), data.highlight_box,
                      fill=hex_to_rgb("#FFFFFF"), font=self.fonts["body_l"],
                      anchor="mm")

        self._draw_footer(img, draw, "", data.brand_color)
        return img
