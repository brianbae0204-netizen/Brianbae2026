"""
olive_young.py — 올리브영 랭킹 & 브랜드 순위 수집
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import SCRAPER_HEADERS


@dataclass
class OliveYoungProduct:
    rank:     int
    name:     str
    brand:    str
    price:    str
    category: str
    rating:   Optional[str] = None
    review_count: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None


class OliveYoungScraper:
    """올리브영 베스트/랭킹 스크래퍼"""

    BASE   = "https://www.oliveyoung.co.kr"
    BEST   = BASE + "/store/main/getBestList.do"
    SEARCH = BASE + "/store/search/getSearchMain.do"

    CATEGORY_MAP = {
        "스킨케어": "10000010001",
        "마스크팩": "10000010010",
        "선케어":   "10000010008",
        "색조":     "10000020001",
        "헤어":     "10000030001",
        "바디":     "10000040001",
        "클렌징":   "10000010007",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(SCRAPER_HEADERS)
        self.session.headers["Referer"] = self.BASE

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def fetch_best_products(self, category: str = "스킨케어",
                            limit: int = 10) -> List[OliveYoungProduct]:
        """카테고리별 베스트 순위"""
        products = []
        cat_code = self.CATEGORY_MAP.get(category, "10000010001")
        params = {
            "cateCode": cat_code,
            "pageIdx":  1,
        }
        try:
            resp = self.session.get(self.BEST, params=params, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")
            items = soup.select("li.flag-item")[:limit]
            for i, item in enumerate(items, 1):
                name_tag  = item.select_one("p.tx-name")
                brand_tag = item.select_one("span.tx-brand")
                price_tag = item.select_one("span.tx-cur")
                img_tag   = item.select_one("img.prd-img")
                a_tag     = item.select_one("a")
                rating_tag = item.select_one("span.score-num")
                review_tag = item.select_one("span.count")

                products.append(OliveYoungProduct(
                    rank=i,
                    name=name_tag.text.strip()  if name_tag  else f"상품{i}",
                    brand=brand_tag.text.strip() if brand_tag else "",
                    price=price_tag.text.strip() if price_tag else "",
                    category=category,
                    rating=rating_tag.text.strip() if rating_tag else None,
                    review_count=review_tag.text.strip() if review_tag else None,
                    image_url=img_tag.get("src", "") if img_tag else None,
                    url=self.BASE + a_tag.get("href", "") if a_tag else None,
                ))
        except Exception as e:
            logger.warning(f"올리브영 베스트 스크래핑 실패 [{category}]: {e}")
            products = self._mock_products(category, limit)
        return products

    def search_brand_rank(self, brand_name: str,
                          category: str = "전체") -> List[OliveYoungProduct]:
        """브랜드명으로 올리브영 내 순위 조회"""
        products = []
        try:
            params = {
                "query":   brand_name,
                "t_page":  1,
                "t_click": "searchbarPC",
            }
            resp = self.session.get(self.SEARCH, params=params, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")
            items = soup.select("div.prd-item")[:10]
            for i, item in enumerate(items, 1):
                name_tag  = item.select_one("p.prd-name")
                brand_tag = item.select_one("p.prd-brand")
                price_tag = item.select_one("span.prd-price-sale")
                rank_tag  = item.select_one("span.num")
                a_tag     = item.select_one("a.prd-thumb")
                products.append(OliveYoungProduct(
                    rank=int(rank_tag.text) if rank_tag and rank_tag.text.isdigit() else i,
                    name=name_tag.text.strip()  if name_tag  else "",
                    brand=brand_tag.text.strip() if brand_tag else brand_name,
                    price=price_tag.text.strip() if price_tag else "",
                    category=category,
                    url=self.BASE + a_tag.get("href", "") if a_tag else None,
                ))
        except Exception as e:
            logger.warning(f"올리브영 브랜드 검색 실패: {e}")
        return products

    @staticmethod
    def _mock_products(category: str, n: int) -> List[OliveYoungProduct]:
        names = ["세럼", "토너", "선크림", "크림", "클렌징폼",
                 "에센스", "앰플", "마스크팩", "미스트", "로션"]
        brands = ["이니스프리", "라네즈", "아이오페", "헤라", "설화수",
                  "클리오", "닥터자르트", "에스트라", "코스알엑스", "에뛰드"]
        return [
            OliveYoungProduct(
                rank=i+1,
                name=f"{brands[i % len(brands)]} {names[i % len(names)]}",
                brand=brands[i % len(brands)],
                price=f"{(i+1)*9800:,}원",
                category=category,
                rating=f"{4.5 - i*0.05:.1f}",
                review_count=f"{(1000 - i*80):,}",
            )
            for i in range(n)
        ]
