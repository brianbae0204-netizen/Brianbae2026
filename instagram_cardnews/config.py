"""
config.py — 환경 변수 로드 및 전역 설정
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# .env 파일 로드 (없어도 오류 없음)
load_dotenv()

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
FONTS_DIR  = Path(os.getenv("FONTS_DIR",  BASE_DIR / "fonts"))

# ─── 디렉토리 자동 생성 ──────────────────────────────────────────────
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FONTS_DIR.mkdir(parents=True, exist_ok=True)


class InstagramConfig:
    USERNAME: str = os.getenv("INSTAGRAM_USERNAME", "")
    PASSWORD: str = os.getenv("INSTAGRAM_PASSWORD", "")


class APIKeys:
    ANTHROPIC:       str = os.getenv("ANTHROPIC_API_KEY", "")
    DART:            str = os.getenv("DART_API_KEY", "")
    NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")
    AMAZON_ACCESS:   str = os.getenv("AMAZON_ACCESS_KEY", "")
    AMAZON_SECRET:   str = os.getenv("AMAZON_SECRET_KEY", "")
    AMAZON_TAG:      str = os.getenv("AMAZON_PARTNER_TAG", "")
    AMAZON_REGION:   str = os.getenv("AMAZON_REGION", "us-east-1")


class CardConfig:
    """카드뉴스 이미지 규격"""
    WIDTH:  int = 1080
    HEIGHT: int = 1080
    BG_COLOR_START: str = "#0F0F1A"   # 다크 그라디언트 시작
    BG_COLOR_END:   str = "#1A1A2E"   # 다크 그라디언트 끝
    ACCENT:         str = "#E91E8C"   # 메인 포인트 컬러 (핫핑크)
    ACCENT_SEC:     str = "#00D4FF"   # 보조 포인트 컬러 (사이안)
    TEXT_PRIMARY:   str = "#FFFFFF"
    TEXT_SECONDARY: str = "#B0BEC5"
    POSITIVE_COLOR: str = "#00E676"   # 워터폴 양수 (초록)
    NEGATIVE_COLOR: str = "#FF1744"   # 워터폴 음수 (빨강)
    TOTAL_COLOR:    str = "#2979FF"   # 워터폴 합계 (파랑)

    # 폰트 (시스템 fallback → Noto Sans KR)
    FONT_REGULAR: str = "NotoSansKR-Regular.otf"
    FONT_BOLD:    str = "NotoSansKR-Bold.otf"
    FONT_LIGHT:   str = "NotoSansKR-Light.otf"


class SchedulerConfig:
    POST_TIMES: List[str] = os.getenv("POST_TIMES", "09:00,18:00").split(",")
    TIMEZONE:   str = os.getenv("TIMEZONE", "Asia/Seoul")


SCRAPER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
