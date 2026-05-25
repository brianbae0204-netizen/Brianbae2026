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
    """카드뉴스 이미지 규격 (다크 테마 — 레거시)"""
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


class EditorialTheme:
    """
    화이트 에디토리얼 카드뉴스 규격 (kodeok.kr 톤&매너 기반)
      • 인스타그램 4:5 세로형 (1080×1350) — 피드에서 가장 크게 노출
      • 큰 볼드 제목 + 구분선 + 강조 본문 + 회색 콜아웃 + 하단 사진 + 페이지 점
    """
    WIDTH:  int = 1080
    HEIGHT: int = 1350

    # ── 색상 ──────────────────────────────────────────────
    BG:            str = "#FFFFFF"   # 순백 배경
    BG_ALT:        str = "#FAFAFA"   # 살짝 회색 배경 (변형용)
    TITLE:         str = "#111111"   # 제목 (거의 검정)
    BODY:          str = "#2B2B2B"   # 본문
    BODY_LIGHT:    str = "#6B6B6B"   # 보조 본문
    DIVIDER:       str = "#111111"   # 구분선 (검정)
    CALLOUT_BG:    str = "#F3F3F3"   # 콜아웃 박스 배경 (연회색)
    CALLOUT_BAR:   str = "#111111"   # 콜아웃 좌측 강조 바
    DOT_ON:        str = "#111111"   # 현재 페이지 점
    DOT_OFF:       str = "#D5D5D5"   # 비활성 페이지 점

    # 포인트(브랜드) 컬러 — 강조 단어/숫자에만 사용
    ACCENT:        str = "#E2452A"   # 강조 레드 (kodeok 느낌)
    ACCENT_BLUE:   str = "#2563EB"
    ACCENT_GREEN:  str = "#16A34A"

    # ── 손익 Sankey 차트 색상 (ekke.now 기반) ────────────────
    SANKEY_REVENUE: str = "#3B82F6"   # 매출 (파랑)
    SANKEY_PROFIT:  str = "#22C55E"   # 이익 (초록)
    SANKEY_COST:    str = "#EF4444"   # 비용 (빨강)
    SANKEY_COST_LT: str = "#F5B5B5"   # 비용 리본 (연빨강)
    SANKEY_REV_LT:  str = "#BBD3FB"   # 매출 리본 (연파랑)
    SANKEY_PRO_LT:  str = "#A7E3BF"   # 이익 리본 (연초록)

    # ── 여백 ──────────────────────────────────────────────
    MARGIN_X:      int = 80
    MARGIN_TOP:    int = 110
    MARGIN_BOTTOM: int = 90

    # ── 폰트 크기 (시인성 강화 — 큰 글씨) ────────────────────
    F_LOGO:     int = 30
    F_PAGE:     int = 26
    F_KICKER:   int = 30     # 제목 위 작은 라벨
    F_TITLE:    int = 70     # 메인 제목 (볼드, 대형)
    F_TITLE_SM: int = 56     # 제목이 길 때
    F_SUBTITLE: int = 34
    F_BODY:     int = 38     # 본문 (크게)
    F_BODY_SM:  int = 32
    F_CALLOUT:  int = 38     # 콜아웃 본문
    F_CAPTION:  int = 24
    F_BIG_NUM:  int = 96     # 초대형 강조 숫자


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
