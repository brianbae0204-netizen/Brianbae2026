"""
google_trends.py — Google Trends / 네이버 데이터랩 트렌드 수집
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests
from loguru import logger

try:
    from pytrends.request import TrendReq
    PYTRENDS_OK = True
except ImportError:
    PYTRENDS_OK = False
    logger.warning("pytrends 미설치 → Google Trends 비활성화")

from config import APIKeys, SCRAPER_HEADERS


@dataclass
class TrendPoint:
    date:  str
    value: int   # 0-100 (구글 트렌드 상대 지수)


@dataclass
class TrendSummary:
    brand_name:     str
    weekly_trend:   List[TrendPoint] = field(default_factory=list)   # 최근 12주
    monthly_trend:  List[TrendPoint] = field(default_factory=list)   # 최근 12개월
    related_queries: List[str]       = field(default_factory=list)
    peak_period:    str              = ""
    trend_direction: str             = ""   # "상승", "하락", "보합"
    interest_score: int              = 0    # 현재 관심도 (0-100)
    regions:        Dict[str, int]   = field(default_factory=dict)   # 지역별 관심도
    naver_trend:    List[TrendPoint] = field(default_factory=list)   # 네이버 데이터랩


class GoogleTrendsScraper:
    """Google Trends + 네이버 데이터랩 트렌드 수집"""

    NAVER_DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(SCRAPER_HEADERS)
        if PYTRENDS_OK:
            try:
                self.pytrends = TrendReq(hl="ko-KR", tz=540, timeout=(10, 30))
            except Exception:
                self.pytrends = None
        else:
            self.pytrends = None

    # ──────────────────────────────────────────────────────────────
    # 1. Google Trends
    # ──────────────────────────────────────────────────────────────
    def _fetch_google_trends(self, brand_name: str) -> Dict:
        if not self.pytrends:
            return {}
        try:
            self.pytrends.build_payload(
                kw_list=[brand_name],
                timeframe="today 12-m",
                geo="KR"
            )
            interest = self.pytrends.interest_over_time()
            related  = self.pytrends.related_queries()
            regions  = self.pytrends.interest_by_region(resolution="COUNTRY")
            return {
                "interest": interest,
                "related":  related,
                "regions":  regions,
            }
        except Exception as e:
            logger.warning(f"Google Trends 오류: {e}")
            return {}

    # ──────────────────────────────────────────────────────────────
    # 2. 네이버 데이터랩 검색어 트렌드
    # ──────────────────────────────────────────────────────────────
    def _fetch_naver_datalab(self, brand_name: str) -> List[TrendPoint]:
        if not (APIKeys.NAVER_CLIENT_ID and APIKeys.NAVER_CLIENT_SECRET):
            return []
        import datetime
        today = datetime.date.today()
        start = (today.replace(year=today.year - 1)).strftime("%Y-%m-%d")
        end   = today.strftime("%Y-%m-%d")
        body = {
            "startDate": start,
            "endDate":   end,
            "timeUnit":  "month",
            "keywordGroups": [
                {"groupName": brand_name, "keywords": [brand_name]}
            ]
        }
        headers = {
            **SCRAPER_HEADERS,
            "X-Naver-Client-Id":     APIKeys.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": APIKeys.NAVER_CLIENT_SECRET,
            "Content-Type":          "application/json",
        }
        try:
            resp = self.session.post(
                self.NAVER_DATALAB_URL, json=body, headers=headers, timeout=10
            )
            data = resp.json()
            results = data.get("results", [])
            if results:
                return [
                    TrendPoint(date=d["period"], value=int(d["ratio"] * 100))
                    for d in results[0].get("data", [])
                ]
        except Exception as e:
            logger.warning(f"네이버 데이터랩 오류: {e}")
        return []

    # ──────────────────────────────────────────────────────────────
    # 3. 목 트렌드 데이터
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _mock_trend(brand: str) -> TrendSummary:
        import random
        import datetime
        today = datetime.date.today()
        # 상승 트렌드 시뮬레이션
        base = 45
        weekly = []
        for w in range(12, 0, -1):
            dt = today - datetime.timedelta(weeks=w)
            val = min(100, max(10, base + random.randint(-8, 15)))
            base = val
            weekly.append(TrendPoint(date=str(dt), value=val))

        monthly = []
        base = 40
        for m in range(12, 0, -1):
            month = today.month - m
            year  = today.year + month // 12
            month = month % 12 or 12
            val = min(100, max(10, base + random.randint(-5, 12)))
            base = val
            monthly.append(TrendPoint(date=f"{year}-{month:02d}-01", value=val))

        return TrendSummary(
            brand_name=brand,
            weekly_trend=weekly,
            monthly_trend=monthly,
            related_queries=[
                f"{brand} 후기",
                f"{brand} 성분",
                f"{brand} 추천",
                f"{brand} 할인",
                "k뷰티 추천",
            ],
            peak_period="2024년 Q4",
            trend_direction="📈 상승",
            interest_score=weekly[-1].value if weekly else 60,
            regions={"서울": 100, "경기": 87, "부산": 65, "인천": 54, "대구": 48},
            naver_trend=monthly[:6],
        )

    # ──────────────────────────────────────────────────────────────
    # 공개 인터페이스
    # ──────────────────────────────────────────────────────────────
    def fetch(self, brand_name: str) -> TrendSummary:
        logger.info(f"[Trends] '{brand_name}' 트렌드 수집")

        # Naver DataLab 먼저 시도
        naver_pts = self._fetch_naver_datalab(brand_name)

        # Google Trends
        g_data = self._fetch_google_trends(brand_name)

        if not g_data and not naver_pts:
            logger.info("트렌드 API 없음 → 목 데이터 사용")
            return self._mock_trend(brand_name)

        summary = self._mock_trend(brand_name)  # 기본 구조
        if naver_pts:
            summary.naver_trend = naver_pts
        if g_data:
            interest_df = g_data.get("interest")
            if interest_df is not None and not interest_df.empty:
                col = brand_name
                if col in interest_df.columns:
                    pts = [
                        TrendPoint(date=str(idx.date()), value=int(val))
                        for idx, val in interest_df[col].items()
                    ]
                    summary.monthly_trend = pts[-12:]
                    summary.interest_score = pts[-1].value if pts else 60

        logger.success(f"[Trends] '{brand_name}' 완료")
        return summary
