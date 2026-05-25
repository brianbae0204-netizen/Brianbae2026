"""
editorial_templates.py — 화이트 에디토리얼 카드뉴스 템플릿
  • kodeok.kr 톤&매너: 큰 볼드 제목 + 검정 구분선 + **강조** 본문 + 회색 콜아웃 + 하단 사진 + 페이지 점
  • 인스타 4:5 세로형 (1080×1350), 시인성 강화 대형 폰트
  • 카드별 사진 임베딩 지원
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from loguru import logger

from config import EditorialTheme as ET
from utils.image_utils import load_korean_font, hex_to_rgb, draw_rounded_rect
from utils.image_fetch import build_photo_strip, build_hero

W, H = ET.WIDTH, ET.HEIGHT


# ══════════════════════════════════════════════════════════════════════
# 인라인 **볼드** 텍스트 렌더링
# ══════════════════════════════════════════════════════════════════════
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _split_bold(text: str) -> List[Tuple[str, bool]]:
    """'a **b** c' → [('a ', False), ('b', True), (' c', False)]"""
    segs: List[Tuple[str, bool]] = []
    idx = 0
    for m in _BOLD_RE.finditer(text):
        if m.start() > idx:
            segs.append((text[idx:m.start()], False))
        segs.append((m.group(1), True))
        idx = m.end()
    if idx < len(text):
        segs.append((text[idx:], False))
    return segs or [(text, False)]


def _text_w(draw, text, font) -> int:
    return int(draw.textlength(text, font=font))


def _wrap_segments(draw, text: str, reg: ImageFont.FreeTypeFont,
                   bold: ImageFont.FreeTypeFont, max_w: int) -> List[List[Tuple]]:
    """**볼드** 마크업 텍스트를 max_w 폭에 맞춰 줄바꿈.
    반환: 줄 리스트, 각 줄은 (글자, is_bold) 토큰 리스트(문자 단위)."""
    segs = _split_bold(text)
    lines: List[List[Tuple]] = []
    cur: List[Tuple] = []
    cur_w = 0
    for content, is_bold in segs:
        font = bold if is_bold else reg
        # 한국어는 글자 단위, 영어는 단어 보존을 위해 공백 기준 토큰화
        tokens = re.findall(r"\s+|[^\s]", content)
        for tok in tokens:
            tw = _text_w(draw, tok, font)
            if cur_w + tw > max_w and cur and tok.strip():
                lines.append(cur)
                cur, cur_w = [], 0
            cur.append((tok, is_bold))
            cur_w += tw
    if cur:
        lines.append(cur)
    return lines


def _draw_rich(draw, x: int, y: int, line: List[Tuple],
               reg, bold, color, bold_color=None) -> int:
    """한 줄(토큰 리스트) 렌더, 다음 x 반환."""
    bold_color = bold_color or color
    cx = x
    for tok, is_bold in line:
        font = bold if is_bold else reg
        draw.text((cx, y), tok, font=font,
                  fill=hex_to_rgb(bold_color if is_bold else color))
        cx += _text_w(draw, tok, font)
    return cx


# ══════════════════════════════════════════════════════════════════════
# 에디토리얼 카드 빌더
# ══════════════════════════════════════════════════════════════════════
class EditorialCard:
    def __init__(self):
        self.f_logo    = load_korean_font(ET.F_LOGO)
        self.f_page    = load_korean_font(ET.F_PAGE)
        self.f_kicker  = load_korean_font(ET.F_KICKER)
        self.f_title   = load_korean_font(ET.F_TITLE)
        self.f_title_b = self._bold(ET.F_TITLE)
        self.f_title_sm = self._bold(ET.F_TITLE_SM)
        self.f_sub     = load_korean_font(ET.F_SUBTITLE)
        self.f_body    = load_korean_font(ET.F_BODY)
        self.f_body_b  = self._bold(ET.F_BODY)
        self.f_body_sm = load_korean_font(ET.F_BODY_SM)
        self.f_callout = load_korean_font(ET.F_CALLOUT)
        self.f_callout_b = self._bold(ET.F_CALLOUT)
        self.f_caption = load_korean_font(ET.F_CAPTION)
        self.f_bignum  = self._bold(ET.F_BIG_NUM)

    @staticmethod
    def _bold(size: int) -> ImageFont.FreeTypeFont:
        from config import FONTS_DIR
        for name in ("NotoSansKR-Bold.otf", "NotoSansKR-Regular.otf"):
            p = FONTS_DIR / name
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except Exception:
                    pass
        return load_korean_font(size)

    # ──────────────────────────────────────────────────────────────
    def _canvas(self, bg: str = ET.BG) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (W, H), hex_to_rgb(bg))
        return img, ImageDraw.Draw(img)

    def _header(self, draw, brand_name: str, page: int, total: int,
                accent: str):
        # 로고 (좌상단) — 브랜드명 대문자
        logo = brand_name.upper()
        draw.text((ET.MARGIN_X, 56), logo, font=self.f_logo,
                  fill=hex_to_rgb(ET.TITLE))
        # 포인트 점
        lw = _text_w(draw, logo, self.f_logo)
        draw.ellipse([ET.MARGIN_X + lw + 8, 64, ET.MARGIN_X + lw + 22, 78],
                     fill=hex_to_rgb(accent))
        # 페이지 뱃지 (우상단)
        badge = f"{page} / {total}"
        bw = _text_w(draw, badge, self.f_page)
        bx = W - ET.MARGIN_X - bw - 28
        draw_rounded_rect(draw, (bx, 52, W - ET.MARGIN_X, 92),
                          radius=20, fill=hex_to_rgb("#111111"))
        draw.text((bx + 14, 60), badge, font=self.f_page,
                  fill=hex_to_rgb("#FFFFFF"))

    def _page_dots(self, draw, page: int, total: int, accent: str):
        r = 7
        gap = 26
        total_w = total * gap
        x = (W - total_w) // 2 + gap // 2
        y = H - 50
        for i in range(total):
            on = (i == page - 1)
            color = ET.DOT_ON if on else ET.DOT_OFF
            rr = r + 2 if on else r
            draw.ellipse([x - rr, y - rr, x + rr, y + rr],
                         fill=hex_to_rgb(color))
            x += gap

    def _kicker(self, draw, y: int, text: str, accent: str) -> int:
        if not text:
            return y
        # 짧은 악센트 바 + 라벨
        draw.rectangle([ET.MARGIN_X, y + 6, ET.MARGIN_X + 40, y + 12],
                       fill=hex_to_rgb(accent))
        draw.text((ET.MARGIN_X + 54, y - 6), text, font=self.f_kicker,
                  fill=hex_to_rgb(accent))
        return y + 44

    def _title(self, draw, y: int, title: str) -> int:
        font = self.f_title_b
        # 너무 길면 작은 볼드
        longest = max((len(l) for l in title.split("\n")), default=0)
        if longest > 13:
            font = self.f_title_sm
        for line in title.split("\n"):
            draw.text((ET.MARGIN_X, y), line, font=font,
                      fill=hex_to_rgb(ET.TITLE))
            asc, desc = font.getmetrics()
            y += asc + desc + 6
        return y

    def _divider(self, draw, y: int) -> int:
        draw.rectangle([ET.MARGIN_X, y, W - ET.MARGIN_X, y + 4],
                       fill=hex_to_rgb(ET.DIVIDER))
        return y + 4

    def _body(self, draw, y: int, lines: List[str], max_w: int,
              accent: str, line_gap: int = 16, para_gap: int = 14) -> int:
        for para in lines:
            wrapped = _wrap_segments(draw, para, self.f_body, self.f_body_b, max_w)
            for ln in wrapped:
                _draw_rich(draw, ET.MARGIN_X, y, ln,
                           self.f_body, self.f_body_b,
                           ET.BODY, accent)
                asc, desc = self.f_body.getmetrics()
                y += asc + desc + line_gap
            y += para_gap
        return y

    def _callout(self, draw, y: int, lines: List[str], max_w: int,
                 accent: str, max_h: Optional[int] = None) -> int:
        if not lines:
            return y
        pad = 30
        line_h = self.f_callout.getmetrics()
        lh = line_h[0] + line_h[1] + 14
        # max_h 가 주어지면 들어갈 수 있는 줄 수만큼만 표시
        if max_h is not None:
            fit = max(1, (max_h - pad * 2) // lh)
            lines = lines[:fit]
        box_h = pad * 2 + lh * len(lines)
        x0, x1 = ET.MARGIN_X, W - ET.MARGIN_X
        draw_rounded_rect(draw, (x0, y, x1, y + box_h),
                          radius=18, fill=hex_to_rgb(ET.CALLOUT_BG))
        draw.rounded_rectangle([x0, y, x0 + 10, y + box_h],
                               radius=5, fill=hex_to_rgb(accent))
        ty = y + pad
        for ln in lines:
            _draw_rich(draw, x0 + pad + 14, ty,
                       _wrap_segments(draw, ln, self.f_callout,
                                      self.f_callout_b,
                                      max_w - pad * 2 - 20)[0],
                       self.f_callout, self.f_callout_b, ET.TITLE, accent)
            ty += lh
        return y + box_h + 20

    def _big_number(self, draw, y: int, number: str, label: str,
                    accent: str) -> int:
        if not number:
            return y
        draw.text((ET.MARGIN_X, y), number, font=self.f_bignum,
                  fill=hex_to_rgb(accent))
        asc, desc = self.f_bignum.getmetrics()
        ny = y + asc + desc
        if label:
            draw.text((ET.MARGIN_X + 6, ny - 6), label, font=self.f_sub,
                      fill=hex_to_rgb(ET.BODY_LIGHT))
            a2, d2 = self.f_sub.getmetrics()
            ny += a2 + d2
        return ny + 10

    def _closing(self, draw, y: int, text: str, accent: str):
        if not text:
            return
        draw.text((ET.MARGIN_X, y), text, font=self.f_body_sm,
                  fill=hex_to_rgb(accent))

    def _photo_band(self, img: Image.Image,
                    photos: List[Optional[Image.Image]],
                    labels: List[str], brand_color: str,
                    band_h: int = 340):
        """하단 풀폭 사진 밴드"""
        if not photos:
            return
        y0 = H - band_h - 70
        strip = build_photo_strip(
            photos, (W, band_h), gap=6, radius=0,
            brand_color=brand_color, labels=labels)
        img.paste(strip, (0, y0))

    # ══════════════════════════════════════════════════════════════
    # 카드 1 — 커버 (풀 히어로 이미지 + 하단 큰 제목)
    # ══════════════════════════════════════════════════════════════
    def cover(self, brand_name: str, copy, hero_img: Optional[Image.Image],
              accent: str, total: int) -> Image.Image:
        img, draw = self._canvas(ET.BG)
        # 상단 히어로 (52% — 하단 텍스트 여백 확보)
        hero_h = int(H * 0.52)
        hero = build_hero(hero_img, (W, hero_h), accent,
                          label=brand_name, darken=0.18)
        img.paste(hero, (0, 0))
        draw = ImageDraw.Draw(img)

        # 히어로 위 로고/페이지
        draw.text((ET.MARGIN_X, 56), brand_name.upper(), font=self.f_logo,
                  fill=hex_to_rgb("#FFFFFF"))
        badge = f"1 / {total}"
        bw = _text_w(draw, badge, self.f_page)
        draw.text((W - ET.MARGIN_X - bw, 58), badge, font=self.f_page,
                  fill=hex_to_rgb("#FFFFFF"))

        # 하단 텍스트 영역
        y = hero_h + 50
        y = self._kicker(draw, y, copy.kicker or "BRAND DEEP DIVE", accent)
        y += 8
        y = self._title(draw, y, copy.title or f"{brand_name}")
        y += 10
        y = self._divider(draw, y)
        y += 28
        y = self._body(draw, y, copy.body or [], W - ET.MARGIN_X * 2, accent)

        # 하단 화살표 (본문 뒤, 페이지 점 위)
        if copy.closing:
            cy = min(y + 22, H - 96)
            draw.text((ET.MARGIN_X, cy), copy.closing,
                      font=self.f_body_sm, fill=hex_to_rgb(accent))
        self._page_dots(draw, 1, total, accent)
        return img

    # ══════════════════════════════════════════════════════════════
    # 표준 카드 (개요/성분/랭킹/투자/트렌드/요약)
    # ══════════════════════════════════════════════════════════════
    def standard(self, brand_name: str, copy, page: int, total: int,
                 accent: str,
                 photos: Optional[List[Optional[Image.Image]]] = None,
                 photo_labels: Optional[List[str]] = None,
                 photo_band_h: int = 320) -> Image.Image:
        img, draw = self._canvas(ET.BG)
        self._header(draw, brand_name, page, total, accent)

        max_w = W - ET.MARGIN_X * 2
        # 콘텐츠 영역 하한 (사진 밴드가 있으면 그 위까지)
        content_limit = (H - photo_band_h - 70 - 24) if photos else (H - 110)

        y = ET.MARGIN_TOP + 30
        y = self._kicker(draw, y, copy.kicker, accent)
        y += 10
        y = self._title(draw, y, copy.title)
        y += 12
        y = self._divider(draw, y)
        y += 34

        if copy.big_number:
            y = self._big_number(draw, y, copy.big_number,
                                 copy.big_number_label, accent)
            y += 14

        y = self._body(draw, y, copy.body, max_w, accent)
        y += 6
        if copy.callout and y < content_limit - 90:
            y = self._callout(draw, y, copy.callout, max_w, accent,
                              max_h=content_limit - y)
        if copy.closing and y < content_limit - 50:
            self._closing(draw, y + 4, copy.closing, accent)

        # 하단 사진 밴드
        if photos:
            self._photo_band(img, photos, photo_labels or [],
                             accent, band_h=photo_band_h)
            draw = ImageDraw.Draw(img)

        self._page_dots(draw, page, total, accent)
        return img

    # ══════════════════════════════════════════════════════════════
    # 손익 카드 (Sankey 차트 전면 배치)
    # ══════════════════════════════════════════════════════════════
    def pl_chart(self, brand_name: str, copy, page: int, total: int,
                 accent: str, chart_img: Optional[Image.Image],
                 kpis: Optional[List[str]] = None) -> Image.Image:
        img, draw = self._canvas(ET.BG)
        self._header(draw, brand_name, page, total, accent)

        y = ET.MARGIN_TOP + 20
        y = self._kicker(draw, y, copy.kicker or "HOW THEY EARN & SPEND", accent)
        y += 8
        y = self._title(draw, y, copy.title or f"{brand_name}는\n이렇게 벌고 쓴다")
        y += 10
        y = self._divider(draw, y)
        y += 20

        # Sankey 차트
        if chart_img:
            cw = W - 40
            ratio = chart_img.height / chart_img.width
            ch = int(cw * ratio)
            max_ch = H - y - 200
            if ch > max_ch:
                ch = max_ch
                cw = int(ch / ratio)
            chart = chart_img.resize((cw, ch), Image.LANCZOS)
            img.paste(chart, ((W - cw) // 2, y))
            y += ch + 10
        else:
            draw.text((W // 2, y + 200), "차트 데이터 없음",
                      font=self.f_body, fill=hex_to_rgb(ET.BODY_LIGHT),
                      anchor="mm")
            y += 420

        draw = ImageDraw.Draw(img)
        # KPI 바
        if kpis:
            ky = H - 150
            draw.rectangle([ET.MARGIN_X, ky - 12, W - ET.MARGIN_X, ky - 9],
                           fill=hex_to_rgb("#E5E5E5"))
            col_w = (W - ET.MARGIN_X * 2) // max(len(kpis), 1)
            for i, kpi in enumerate(kpis[:4]):
                cx = ET.MARGIN_X + i * col_w + col_w // 2
                if ":" in kpi:
                    k, v = kpi.split(":", 1)
                    draw.text((cx, ky), v.strip(), font=self.f_body_b,
                              fill=hex_to_rgb(accent), anchor="mt")
                    a, d = self.f_body_b.getmetrics()
                    draw.text((cx, ky + a + d), k.strip(),
                              font=self.f_caption,
                              fill=hex_to_rgb(ET.BODY_LIGHT), anchor="mt")
        self._page_dots(draw, page, total, accent)
        return img
