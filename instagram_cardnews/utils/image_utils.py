"""
image_utils.py — Pillow 이미지 유틸리티
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

# Pillow
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import CardConfig, FONTS_DIR


# ──────────────────────────────────────────────────────────────────────
# 한글 폰트 로드
# ──────────────────────────────────────────────────────────────────────

_FONT_CACHE: dict = {}

def load_korean_font_path() -> Optional[Path]:
    """NotoSansKR 폰트 경로 탐색 (없으면 다운로드 시도)"""
    candidates = [
        FONTS_DIR / "NotoSansKR-Bold.otf",
        FONTS_DIR / "NotoSansKR-Regular.otf",
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),           # macOS
        Path("C:/Windows/Fonts/malgun.ttf"),                          # Windows
    ]
    for p in candidates:
        if p.exists():
            return p
    # 자동 다운로드 시도
    return _download_noto_font()


def _download_noto_font() -> Optional[Path]:
    """pip 또는 직접 다운로드로 NotoSansKR 폰트 설치"""
    font_path = FONTS_DIR / "NotoSansKR-Regular.otf"
    if font_path.exists():
        return font_path
    try:
        import urllib.request
        url = (
            "https://raw.githubusercontent.com/googlefonts/noto-cjk/"
            "main/Sans/OTF/Korean/NotoSansCJKkr-Regular.otf"
        )
        logger.info("한글 폰트 다운로드 중...")
        urllib.request.urlretrieve(url, str(font_path))
        logger.success(f"폰트 다운로드 완료: {font_path}")
        return font_path
    except Exception as e:
        logger.warning(f"폰트 다운로드 실패: {e} → 기본 폰트 사용")
        return None


def load_korean_font(size: int = 20) -> ImageFont.FreeTypeFont:
    """크기별 캐싱된 한글 폰트 반환"""
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    path = load_korean_font_path()
    try:
        if path:
            font = ImageFont.truetype(str(path), size)
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    _FONT_CACHE[size] = font
    return font


# ──────────────────────────────────────────────────────────────────────
# 색상 유틸
# ──────────────────────────────────────────────────────────────────────

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """'#RRGGBB' → (R, G, B)"""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))   # type: ignore


def blend_colors(c1: Tuple, c2: Tuple, t: float) -> Tuple:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))  # type: ignore


# ──────────────────────────────────────────────────────────────────────
# 그리기 유틸
# ──────────────────────────────────────────────────────────────────────

def draw_gradient_background(
    img: Image.Image,
    color_start: str = "#0F0F1A",
    color_end:   str = "#1A1A2E",
    direction:   str = "diagonal",   # "vertical" | "horizontal" | "diagonal"
):
    """이미지에 그라디언트 배경 그리기 (in-place)"""
    W, H = img.size
    draw = ImageDraw.Draw(img)
    c1 = hex_to_rgb(color_start)
    c2 = hex_to_rgb(color_end)

    for y in range(H):
        for x in range(W):
            if direction == "vertical":
                t = y / H
            elif direction == "horizontal":
                t = x / W
            else:  # diagonal
                t = (x / W + y / H) / 2
            r, g, b = blend_colors(c1, c2, t)
            draw.point((x, y), fill=(r, g, b))


def draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy:     Tuple[int, int, int, int],
    radius: int = 16,
    fill:   Optional[Tuple] = None,
    outline: Optional[Tuple] = None,
    width:  int = 1,
):
    """둥근 모서리 사각형"""
    x0, y0, x1, y1 = xy
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)

    # RGBA 지원
    if fill:
        draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
        draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
        draw.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill)
        draw.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill)
        draw.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill)
        draw.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill)

    if outline:
        draw.arc([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=outline, width=width)
        draw.arc([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=outline, width=width)
        draw.arc([x0, y1 - 2*r, x0 + 2*r, y1], 90,  180, fill=outline, width=width)
        draw.arc([x1 - 2*r, y1 - 2*r, x1, y1], 0,   90,  fill=outline, width=width)
        draw.line([x0 + r, y0, x1 - r, y0],      fill=outline, width=width)
        draw.line([x0 + r, y1, x1 - r, y1],      fill=outline, width=width)
        draw.line([x0, y0 + r, x0, y1 - r],      fill=outline, width=width)
        draw.line([x1, y0 + r, x1, y1 - r],      fill=outline, width=width)


def draw_glow_text(
    draw:   ImageDraw.ImageDraw,
    xy:     Tuple[int, int],
    text:   str,
    font:   ImageFont.FreeTypeFont,
    color:  str = "#E91E8C",
    anchor: str = "mm",
    blur_radius: int = 6,
):
    """글로우 효과 텍스트 (shadow + main)"""
    glow_color = hex_to_rgb(color)
    for dx in range(-blur_radius, blur_radius + 1, 2):
        for dy in range(-blur_radius, blur_radius + 1, 2):
            alpha = max(0, 100 - (abs(dx) + abs(dy)) * 12)
            draw.text((xy[0] + dx, xy[1] + dy), text,
                      fill=glow_color + (alpha,), font=font, anchor=anchor)
    draw.text(xy, text, fill=hex_to_rgb("#FFFFFF"), font=font, anchor=anchor)


def paste_image_round(
    base:      Image.Image,
    overlay:   Image.Image,
    pos:        Tuple[int, int],
    size:       Tuple[int, int],
    radius:     int = 16,
):
    """둥근 마스크로 이미지 붙이기"""
    overlay = overlay.resize(size, Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, size[0], size[1]], radius=radius, fill=255)
    base.paste(overlay, pos, mask)
