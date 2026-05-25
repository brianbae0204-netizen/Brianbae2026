"""
brand_info.py — 브랜드 기본 정보 & 전성분 수집
  • 네이버 검색 API (브랜드 개요)
  • 올리브영 / 화해 전성분 파싱
  • Naver Shopping 제품 리스트
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import APIKeys, SCRAPER_HEADERS


@dataclass
class IngredientInfo:
    product_name: str
    ingredients: List[str]
    ewg_scores: Dict[str, str] = field(default_factory=dict)   # 성분명: EWG등급
    source: str = ""


@dataclass
class BrandOverview:
    name: str
    name_en: str = ""
    category: str = ""
    founded_year: str = ""
    founder: str = ""
    headquarters: str = ""
    website: str = ""
    description: str = ""
    key_products: List[str] = field(default_factory=list)
    ingredients: List[IngredientInfo] = field(default_factory=list)
    logo_url: str = ""
    tags: List[str] = field(default_factory=list)


class BrandInfoScraper:
    """브랜드 기본 정보 + 전성분 스크래퍼"""

    NAVER_SEARCH_URL = "https://openapi.naver.com/v1/search/news.json"
    NAVER_SHOPPING_URL = "https://openapi.naver.com/v1/search/shop.json"
    HWAHAE_URL = "https://www.hwahae.co.kr/api/v2/products/search"
    OLIVEYOUNG_BASE = "https://www.oliveyoung.co.kr"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(SCRAPER_HEADERS)

    # ──────────────────────────────────────────────────────────────
    # 1. 네이버 검색 API → 브랜드 기사/뉴스
    # ──────────────────────────────────────────────────────────────
    def _naver_search(self, query: str, display: int = 10) -> List[Dict]:
        if not (APIKeys.NAVER_CLIENT_ID and APIKeys.NAVER_CLIENT_SECRET):
            logger.warning("네이버 API 키 없음 → 뉴스 검색 건너뜀")
            return []
        headers = {
            "X-Naver-Client-Id":     APIKeys.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": APIKeys.NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": display, "sort": "date"}
        try:
            resp = self.session.get(self.NAVER_SEARCH_URL, headers=headers,
                                    params=params, timeout=10)
            resp.raise_for_status()
            return resp.json().get("items", [])
        except Exception as e:
            logger.error(f"Naver search error: {e}")
            return []

    def _naver_shopping(self, query: str, display: int = 5) -> List[Dict]:
        if not (APIKeys.NAVER_CLIENT_ID and APIKeys.NAVER_CLIENT_SECRET):
            return []
        headers = {
            "X-Naver-Client-Id":     APIKeys.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": APIKeys.NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": display, "sort": "sim"}
        try:
            resp = self.session.get(self.NAVER_SHOPPING_URL, headers=headers,
                                    params=params, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return items
        except Exception as e:
            logger.error(f"Naver shopping error: {e}")
            return []

    # ──────────────────────────────────────────────────────────────
    # 2. 화해 API → 전성분
    # ──────────────────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def _fetch_hwahae_ingredients(self, brand_name: str) -> List[IngredientInfo]:
        """화해(hwahae) 앱 API로 전성분 수집"""
        results = []
        try:
            params = {"keyword": brand_name, "page": 1, "pageSize": 5}
            resp = self.session.get(self.HWAHAE_URL, params=params, timeout=15)
            if resp.status_code != 200:
                return results
            data = resp.json()
            products = data.get("data", {}).get("products", [])
            for p in products[:3]:
                pid = p.get("id")
                pname = p.get("name", "")
                ing_list = p.get("ingredients", [])
                if isinstance(ing_list, list):
                    names = [i.get("name", "") for i in ing_list if i.get("name")]
                    results.append(IngredientInfo(
                        product_name=pname,
                        ingredients=names,
                        source="화해"
                    ))
        except Exception as e:
            logger.warning(f"화해 API 오류: {e}")
        return results

    # ──────────────────────────────────────────────────────────────
    # 3. 올리브영 상품 페이지 → 전성분
    # ──────────────────────────────────────────────────────────────
    def _fetch_oliveyoung_ingredients(self, brand_name: str) -> List[IngredientInfo]:
        results = []
        try:
            search_url = (
                f"https://www.oliveyoung.co.kr/store/search/getSearchMain.do"
                f"?query={requests.utils.quote(brand_name)}&t_page=1&t_click=searchbarPC"
            )
            resp = self.session.get(search_url, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")
            product_links = soup.select("a.prd-thumb")[:3]
            for link in product_links:
                href = link.get("href", "")
                if not href.startswith("http"):
                    href = self.OLIVEYOUNG_BASE + href
                time.sleep(1.0)
                try:
                    ppage = self.session.get(href, timeout=15)
                    psoup = BeautifulSoup(ppage.text, "lxml")
                    # 상품명
                    pname_tag = psoup.select_one("p.prd-name")
                    pname = pname_tag.text.strip() if pname_tag else "Unknown"
                    # 전성분
                    ing_tag = psoup.select_one("div.ingredient-wrap p")
                    if ing_tag:
                        raw = ing_tag.text.strip()
                        ing_list = [i.strip() for i in re.split(r"[,，]", raw) if i.strip()]
                        results.append(IngredientInfo(
                            product_name=pname,
                            ingredients=ing_list[:30],
                            source="올리브영"
                        ))
                except Exception as inner:
                    logger.debug(f"올리브영 제품 파싱 실패: {inner}")
        except Exception as e:
            logger.warning(f"올리브영 전성분 오류: {e}")
        return results

    # ──────────────────────────────────────────────────────────────
    # 4. 종합 브랜드 정보 수집
    # ──────────────────────────────────────────────────────────────
    def fetch(self, brand_name: str) -> BrandOverview:
        logger.info(f"[BrandInfo] '{brand_name}' 브랜드 정보 수집 시작")
        overview = BrandOverview(name=brand_name)

        # ① 네이버 뉴스 → 설립연도/창업자 추출
        news_items = self._naver_search(f"{brand_name} 브랜드 설립 창업자")
        for item in news_items[:5]:
            desc = BeautifulSoup(item.get("description", ""), "html.parser").text
            # 설립연도 정규식
            if not overview.founded_year:
                m = re.search(r"(19|20)\d{2}년", desc)
                if m:
                    overview.founded_year = m.group(0)
            # 창업자
            if not overview.founder:
                m = re.search(r"([가-힣]{2,4})\s*(대표|창업자|설립자|CEO)", desc)
                if m:
                    overview.founder = m.group(1)
        overview.description = self._build_description(brand_name, news_items)

        # ② 네이버 쇼핑 → 주요 제품
        shopping_items = self._naver_shopping(brand_name)
        overview.key_products = list({
            BeautifulSoup(i.get("title", ""), "html.parser").text
            for i in shopping_items
        })[:5]

        # ③ 전성분
        overview.ingredients = self._fetch_hwahae_ingredients(brand_name)
        if not overview.ingredients:
            overview.ingredients = self._fetch_oliveyoung_ingredients(brand_name)

        # ④ 태그 추출
        overview.tags = self._extract_tags(brand_name, news_items, shopping_items)

        logger.success(f"[BrandInfo] '{brand_name}' 수집 완료")
        return overview

    # ──────────────────────────────────────────────────────────────
    # 내부 헬퍼
    # ──────────────────────────────────────────────────────────────
    def _build_description(self, brand: str, news_items: List[Dict]) -> str:
        texts = []
        for item in news_items[:3]:
            desc = BeautifulSoup(item.get("description", ""), "html.parser").text
            texts.append(desc)
        combined = " ".join(texts)
        # 너무 길면 자름
        return combined[:300] if combined else f"{brand} 브랜드 정보"

    def _extract_tags(self, brand: str,
                      news: List[Dict], shopping: List[Dict]) -> List[str]:
        tags: set[str] = set()
        beauty_kw = {"스킨케어", "색조", "선케어", "헤어", "바디", "클렌징",
                     "세럼", "토너", "크림", "마스크", "에센스", "로션"}
        all_text = " ".join(
            BeautifulSoup(i.get("description", "") + i.get("title", ""),
                          "html.parser").text
            for i in (news + shopping)
        )
        for kw in beauty_kw:
            if kw in all_text:
                tags.add(kw)
        return list(tags)[:6]
