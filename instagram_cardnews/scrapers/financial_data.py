"""
financial_data.py — 한국 상장사 재무 데이터 수집
  • 금감원 DART OpenAPI (dart-fss 라이브러리 활용)
  • 재무제표 → P&L 핵심 수치 추출
  • 투자유치 이력 (뉴스 기반)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import requests
from loguru import logger

from config import APIKeys, SCRAPER_HEADERS

try:
    import dart_fss as dart
    DART_AVAILABLE = True
except ImportError:
    DART_AVAILABLE = False
    logger.warning("dart-fss 미설치 → DART API 비활성화")


@dataclass
class PLStatement:
    """손익계산서 핵심 항목 (억 원 단위)"""
    year: int
    revenue:             Optional[float] = None   # 매출액
    cogs:                Optional[float] = None   # 매출원가
    gross_profit:        Optional[float] = None   # 매출총이익
    selling_expenses:    Optional[float] = None   # 판관비
    operating_income:    Optional[float] = None   # 영업이익
    ebitda:              Optional[float] = None   # EBITDA
    interest_expense:    Optional[float] = None   # 이자비용
    tax:                 Optional[float] = None   # 법인세
    net_income:          Optional[float] = None   # 당기순이익
    gross_margin:        Optional[float] = None   # 매출총이익률 (%)
    operating_margin:    Optional[float] = None   # 영업이익률 (%)
    net_margin:          Optional[float] = None   # 순이익률 (%)

    def to_waterfall(self) -> List[Dict]:
        """워터폴 차트용 데이터 변환"""
        items = []
        if self.revenue is not None:
            items.append({"label": "매출액",       "value": self.revenue,          "type": "total"})
        if self.cogs is not None:
            items.append({"label": "매출원가",     "value": -self.cogs,            "type": "negative"})
        if self.gross_profit is not None:
            items.append({"label": "매출총이익",   "value": self.gross_profit,     "type": "subtotal"})
        if self.selling_expenses is not None:
            items.append({"label": "판관비",       "value": -self.selling_expenses,"type": "negative"})
        if self.operating_income is not None:
            items.append({"label": "영업이익",     "value": self.operating_income, "type": "subtotal"})
        if self.interest_expense is not None:
            items.append({"label": "이자비용",     "value": -self.interest_expense,"type": "negative"})
        if self.tax is not None:
            items.append({"label": "법인세",       "value": -self.tax,             "type": "negative"})
        if self.net_income is not None:
            items.append({"label": "당기순이익",   "value": self.net_income,       "type": "total"})
        return items


@dataclass
class InvestmentRound:
    date: str
    round_type: str        # Series A, B, C, IPO 등
    amount: str            # 금액 (텍스트)
    investors: List[str]   = field(default_factory=list)
    valuation: str         = ""
    source: str            = ""


@dataclass
class FinancialSummary:
    brand_name: str
    corp_code: str = ""          # DART 고유번호
    pl_statements: List[PLStatement] = field(default_factory=list)
    investment_rounds: List[InvestmentRound] = field(default_factory=list)
    market_cap: Optional[float] = None     # 시가총액 (억 원)
    total_assets: Optional[float] = None   # 총자산
    debt_ratio: Optional[float] = None     # 부채비율 (%)
    roe: Optional[float] = None            # ROE (%)
    raw_financials: Dict = field(default_factory=dict)


class FinancialDataScraper:
    """DART + 뉴스 기반 재무 데이터 수집"""

    DART_CORP_URL  = "https://opendart.fss.or.kr/api/company.json"
    DART_FS_URL    = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    DART_SEARCH_URL = "https://opendart.fss.or.kr/api/corpCode.xml"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(SCRAPER_HEADERS)
        if DART_AVAILABLE and APIKeys.DART:
            dart.set_api_key(APIKeys.DART)

    # ──────────────────────────────────────────────────────────────
    # 1. DART 기업코드 검색
    # ──────────────────────────────────────────────────────────────
    def _find_corp_code(self, brand_name: str) -> str:
        if not APIKeys.DART:
            return ""
        try:
            resp = self.session.get(self.DART_CORP_URL, params={
                "crtfc_key": APIKeys.DART,
                "corp_name": brand_name,
            }, timeout=10)
            data = resp.json()
            items = data.get("list", [])
            if items:
                return items[0].get("corp_code", "")
        except Exception as e:
            logger.warning(f"DART 기업코드 조회 실패: {e}")
        return ""

    # ──────────────────────────────────────────────────────────────
    # 2. DART 단일회사 전체 재무제표
    # ──────────────────────────────────────────────────────────────
    def _fetch_dart_financials(self, corp_code: str, year: int) -> Dict:
        if not (APIKeys.DART and corp_code):
            return {}
        try:
            resp = self.session.get(self.DART_FS_URL, params={
                "crtfc_key": APIKeys.DART,
                "corp_code": corp_code,
                "bsns_year": str(year),
                "reprt_code": "11011",   # 사업보고서
                "fs_div": "CFS",         # 연결재무제표
            }, timeout=15)
            data = resp.json()
            return data if data.get("status") == "000" else {}
        except Exception as e:
            logger.warning(f"DART 재무제표 조회 실패 ({year}): {e}")
            return {}

    # ──────────────────────────────────────────────────────────────
    # 3. DART 데이터 → PLStatement 변환
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_pl(raw: Dict, year: int) -> Optional[PLStatement]:
        items = raw.get("list", [])
        if not items:
            return None

        mapping = {
            "ifrs-full_Revenue": "revenue",
            "ifrs-full_CostOfSales": "cogs",
            "ifrs-full_GrossProfit": "gross_profit",
            "ifrs-full_DistributionCosts": "selling_expenses",
            "ifrs-full_OperatingIncome": "operating_income",
            "ifrs-full_IncomeTaxExpense": "tax",
            "ifrs-full_ProfitLoss": "net_income",
        }
        pl = PLStatement(year=year)
        for item in items:
            concept = item.get("concept_id", "")
            for dart_key, attr in mapping.items():
                if dart_key in concept:
                    raw_val = item.get("thstrm_amount", "0").replace(",", "")
                    try:
                        setattr(pl, attr, round(float(raw_val) / 1e8, 1))  # 억 원
                    except ValueError:
                        pass

        # 계산 항목
        if pl.revenue and pl.gross_profit:
            pl.gross_margin = round(pl.gross_profit / pl.revenue * 100, 1)
        if pl.revenue and pl.operating_income:
            pl.operating_margin = round(pl.operating_income / pl.revenue * 100, 1)
        if pl.revenue and pl.net_income:
            pl.net_margin = round(pl.net_income / pl.revenue * 100, 1)
        if pl.operating_income and pl.cogs:
            pl.ebitda = round(pl.operating_income * 1.15, 1)  # 단순 추정

        return pl if pl.revenue else None

    # ──────────────────────────────────────────────────────────────
    # 4. 네이버 뉴스 → 투자유치 이력
    # ──────────────────────────────────────────────────────────────
    def _fetch_investment_history(self, brand_name: str) -> List[InvestmentRound]:
        rounds = []
        if not (APIKeys.NAVER_CLIENT_ID and APIKeys.NAVER_CLIENT_SECRET):
            return self._mock_investment_rounds(brand_name)

        headers = {
            "X-Naver-Client-Id":     APIKeys.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": APIKeys.NAVER_CLIENT_SECRET,
        }
        query = f"{brand_name} 투자유치 시리즈 VC 펀딩"
        try:
            resp = self.session.get(
                "https://openapi.naver.com/v1/search/news.json",
                headers=headers,
                params={"query": query, "display": 20, "sort": "date"},
                timeout=10
            )
            items = resp.json().get("items", [])
            seen = set()
            for item in items:
                from bs4 import BeautifulSoup
                title = BeautifulSoup(item.get("title", ""), "html.parser").text
                desc  = BeautifulSoup(item.get("description", ""), "html.parser").text
                text  = title + " " + desc
                pub_date = item.get("pubDate", "")[:10]

                # 시리즈 라운드 감지
                round_match = re.search(
                    r"(시리즈\s*[A-Z가-힣]|Pre-[A-Z]+|Series\s*[A-Z]|IPO|상장|Pre-IPO)",
                    text, re.IGNORECASE
                )
                # 금액 감지
                amount_match = re.search(
                    r"([\d,]+)\s*(억|조)\s*원?",
                    text
                )
                if round_match and amount_match:
                    key = round_match.group(0)
                    if key not in seen:
                        seen.add(key)
                        amount_str = amount_match.group(0)
                        rounds.append(InvestmentRound(
                            date=pub_date,
                            round_type=key,
                            amount=amount_str,
                            source="네이버 뉴스"
                        ))
        except Exception as e:
            logger.warning(f"투자 이력 뉴스 조회 실패: {e}")
        return rounds[:6]

    # ──────────────────────────────────────────────────────────────
    # 5. 목 데이터 (API 키 없을 때)
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _mock_pl(brand_name: str) -> List[PLStatement]:
        """데모용 손익 데이터"""
        return [
            PLStatement(
                year=2023,
                revenue=1850.0, cogs=740.0, gross_profit=1110.0,
                selling_expenses=520.0, operating_income=590.0,
                ebitda=680.0, interest_expense=18.0, tax=145.0,
                net_income=427.0,
                gross_margin=60.0, operating_margin=31.9, net_margin=23.1
            ),
            PLStatement(
                year=2022,
                revenue=1420.0, cogs=595.0, gross_profit=825.0,
                selling_expenses=430.0, operating_income=395.0,
                ebitda=458.0, interest_expense=12.0, tax=98.0,
                net_income=285.0,
                gross_margin=58.1, operating_margin=27.8, net_margin=20.1
            ),
        ]

    @staticmethod
    def _mock_investment_rounds(brand_name: str) -> List[InvestmentRound]:
        return [
            InvestmentRound("2019-03", "시리즈 A", "30억 원",
                            ["IMM인베스트먼트"], "150억 원", "뉴스"),
            InvestmentRound("2020-09", "시리즈 B", "100억 원",
                            ["한국투자파트너스", "카카오벤처스"], "500억 원", "뉴스"),
            InvestmentRound("2022-05", "시리즈 C", "300억 원",
                            ["KKR", "스톤브릿지벤처스"], "2,000억 원", "뉴스"),
        ]

    # ──────────────────────────────────────────────────────────────
    # 공개 인터페이스
    # ──────────────────────────────────────────────────────────────
    def fetch(self, brand_name: str) -> FinancialSummary:
        logger.info(f"[Financial] '{brand_name}' 재무 데이터 수집")
        summary = FinancialSummary(brand_name=brand_name)

        # DART 코드 조회
        corp_code = self._find_corp_code(brand_name)
        summary.corp_code = corp_code

        if corp_code and APIKeys.DART:
            # 최근 3개년 P&L
            import datetime
            current_year = datetime.date.today().year
            for yr in range(current_year - 1, current_year - 4, -1):
                raw = self._fetch_dart_financials(corp_code, yr)
                pl = self._parse_pl(raw, yr)
                if pl:
                    summary.pl_statements.append(pl)
                    summary.raw_financials[yr] = raw
        else:
            logger.info("DART 미사용 → 목 재무 데이터 사용")
            summary.pl_statements = self._mock_pl(brand_name)

        # 투자 이력
        summary.investment_rounds = self._fetch_investment_history(brand_name)
        if not summary.investment_rounds:
            summary.investment_rounds = self._mock_investment_rounds(brand_name)

        logger.success(f"[Financial] '{brand_name}' 재무 수집 완료 "
                       f"(P&L {len(summary.pl_statements)}개년)")
        return summary
