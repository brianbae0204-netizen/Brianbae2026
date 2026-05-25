"""
image_fetch.py — 카드뉴스용 사진 다운로드 & 가공
  • 스크래핑된 제품/브랜드 이미지 URL 다운로드
  • 실패 시 브랜드 컬러 기반 플레이스홀더 생성
  • 하단 사진 스트립 / 단일 히어로 이미지 합성
"""
from __future__ import annotations

import io
import hashlib
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from loguru import logger
from PIL import Image, ImageDraw, ImageFilter

from config import SCRAPER_HEADERS, OUTPUT_DIR
from utils.image_utils import hex_to_rgb, load_korean_font


_CACHE_DIR = OUTPUT_DIR / ".img_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────────────
# URL → PIL.Image (캐싱)
# ──────────────────────────────────────────────────────────────────────
def download_image(url: str, timeout: int = 12) -> Optional[Image.Image]:
    if not url or not url.startswith("http"):
        return None
    key = hashlib.md5(url.encode()).hexdigest()
    cache_path = _CACHE_DIR / f"{key}.png"
    if cache_path.exists():
        try:
            return Image.open(cache_path).convert("RGB")
        except Exception:
            pass
    try:
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=timeout)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        img.save(cache_path, "PNG")
        return img
    except Exception as e:
        logger.debug(f"이미지 다운로드 실패 ({url[:50]}): {e}")
        return None


def download_first_valid(urls: List[str]) -> Optional[Image.Image]:
    """여러 URL 중 처음으로 성공한 이미지 반환"""
    for u in urls:
        img = download_image(u)
        if img:
            return img
    return None


# ──────────────────────────────────────────────────────────────────────
# 커버/채우기 크롭 (object-fit: cover)
# ──────────────────────────────────────────────────────────────────────
def crop_cover(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
    tw, th = size
    sw, sh = img.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top  = (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))


# ──────────────────────────────────────────────────────────────────────
# 브랜드 컬러 플레이스홀더 (사진 없을 때)
# ──────────────────────────────────────────────────────────────────────
def make_placeholder(
    size: Tuple[int, int],
    brand_color: str,
    label: str = "",
    style: str = "gradient",
) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (w, h), hex_to_rgb(brand_color))
    draw = ImageDraw.Draw(base)
    c = hex_to_rgb(brand_color)

    if style == "gradient":
        # 대각 그라디언트 (브랜드색 → 어둡게)
        dark = tuple(int(x * 0.55) for x in c)
        for y in range(h):
            t = y / h
            row = tuple(int(c[i] + (dark[i] - c[i]) * t) for i in range(3))
            draw.line([(0, y), (w, y)], fill=row)
        # 장식 원
        for r, a in [(int(w*0.5), 30), (int(w*0.32), 45)]:
            ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.ellipse([w - r, -r, w + r, r], fill=(255, 255, 255, a))
            base = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")
        draw = ImageDraw.Draw(base)

    if label:
        font = load_korean_font(max(28, h // 8))
        draw.text((w // 2, h // 2), label[:14],
                  fill=(255, 255, 255), font=font, anchor="mm")
    return base


# ──────────────────────────────────────────────────────────────────────
# 라운드 마스크 적용
# ──────────────────────────────────────────────────────────────────────
def rounded(img: Image.Image, radius: int = 24) -> Image.Image:
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, img.size[0], img.size[1]], radius=radius, fill=255)
    img.putalpha(mask)
    return img


# ──────────────────────────────────────────────────────────────────────
# 하단 사진 스트립 (kodeok.kr 스타일: 가로로 2~3장)
# ──────────────────────────────────────────────────────────────────────
def build_photo_strip(
    images: List[Optional[Image.Image]],
    size: Tuple[int, int],
    gap: int = 8,
    radius: int = 0,
    brand_color: str = "#888888",
    labels: Optional[List[str]] = None,
) -> Image.Image:
    """여러 이미지를 가로 스트립으로 합성. None은 플레이스홀더로 대체."""
    w, h = size
    n = max(1, len(images))
    cell_w = (w - gap * (n - 1)) // n
    strip = Image.new("RGB", (w, h), (255, 255, 255))

    x = 0
    for i, img in enumerate(images):
        if img is None:
            lbl = labels[i] if labels and i < len(labels) else ""
            img = make_placeholder((cell_w, h), brand_color, lbl)
        cell = crop_cover(img, (cell_w, h))
        if radius > 0:
            cell = rounded(cell, radius)
            strip.paste(cell, (x, 0), cell)
        else:
            strip.paste(cell, (x, 0))
        x += cell_w + gap
    return strip


# ──────────────────────────────────────────────────────────────────────
# 단일 히어로 이미지 (커버용, 살짝 어둡게 오버레이)
# ──────────────────────────────────────────────────────────────────────
def build_hero(
    img: Optional[Image.Image],
    size: Tuple[int, int],
    brand_color: str,
    label: str = "",
    darken: float = 0.0,
) -> Image.Image:
    if img is None:
        hero = make_placeholder(size, brand_color, label)
    else:
        hero = crop_cover(img, size)
    if darken > 0:
        ov = Image.new("RGBA", size, (0, 0, 0, int(255 * darken)))
        hero = Image.alpha_composite(hero.convert("RGBA"), ov).convert("RGB")
    return hero
