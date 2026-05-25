"""
naver_smartstore.py — 네이버 스마트스토어 & 쇼핑 랭킹 수집
  • 네이버 쇼핑 검색 API
  • 브랜드관 정보
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config import APIKeys, SCRAPER_HEADERS


@dataclass
class NaverProduct:
    rank:        int
    name:        str
    brand:       str
    price:       str
    review_count: Optional[str] = None
    rating:      Optional[str]  = None
    category:    str             = ""
    mall_name:   str             = ""
    product_id:  str             = ""
    link:        str             = ""
    image:       str             = ""
    ad:          bool            = False


class NaverSmartStoreScraper:
    """네이버 쇼핑 랭킹 수집"""

    SHOPPING_API = "https://openapi.naver.com/v1/search/shop.json"
    DATALAB_URL  = "https://datalab.naver.com/shoppingInsight/getCategoryKeyword.naver"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(SCRAPER_HEADERS)

    def _api_headers(self):
        return {
            "X-Naver-Client-Id":     APIKeys.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": APIKeys.NAVER_CLIENT_SECRET,
        }

    # ──────────────────────────────────────────────────────────────
    def fetch_brand_products(self, brand_name: str,
                             display: int = 20) -> List[NaverProduct]:
        """브랜드 쇼핑 검색 순위"""
        if not (APIKeys.NAVER_CLIENT_ID and APIKeys.NAVER_CLIENT_SECRET):
            logger.warning("네이버 API 키 없음 → 목 데이터 사용")
            return self._mock_products(brand_name, display)

        products = []
        try:
            params = {
                "query":   brand_name,
                "display": display,
                "start":   1,
                "sort":    "sim",
            }
            resp = self.session.get(
                self.SHOPPING_API,
                headers=self._api_headers(),
                params=params,
                timeout=10
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            for i, item in enumerate(items, 1):
                title = BeautifulSoup(item.get("title", ""), "html.parser").text
                products.append(NaverProduct(
                    rank=i,
                    name=title,
                    brand=item.get("brand", brand_name),
                    price=f"{int(item.get('lprice', 0)):,}원",
                    review_count=item.get("reviewCount", ""),
                    rating=item.get("score", ""),
                    category=item.get("category1", ""),
                    mall_name=item.get("mallName", ""),
                    product_id=item.get("productId", ""),
                    link=item.get("link", ""),
                    image=item.get("image", ""),
                    ad=item.get("productType", "") == "2",
                ))
        except Exception as e:
            logger.warning(f"네이버 쇼핑 검색 실패: {e}")
            products = self._mock_products(brand_name, display)
        return products

    def fetch_category_rank(self, category: str,
                            limit: int = 10) -> List[NaverProduct]:
        """카테고리 인기 키워드 기반 상품 순위"""
        return self.fetch_brand_products(category, limit)

    def get_brand_store_info(self, brand_name: str) -> dict:
        """스마트스토어 브랜드관 기본 정보"""
        try:
            url = f"https://smartstore.naver.com/{brand_name.lower().replace(' ', '')}"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                store_name = soup.select_one("h1.store-name")
                followers   = soup.select_one("span.follower-cnt")
                return {
                    "url":       url,
                    "name":      store_name.text.strip() if store_name else brand_name,
                    "followers": followers.text.strip() if followers else "N/A",
                    "status":    "active",
                }
        except Exception:
            pass
        return {"url": "", "name": brand_name, "followers": "N/A", "status": "unknown"}

    @staticmethod
    def _mock_products(brand: str, n: int) -> List[NaverProduct]:
        items = [
            ("세럼 30ml", "36,000원", "4.8", "2,341"),
            ("토너 150ml", "24,000원", "4.7", "5,892"),
            ("크림 50ml", "45,000원", "4.9", "1,203"),
            ("선크림 SPF50+", "29,000원", "4.6", "8,721"),
            ("앰플 30ml",   "52,000원", "4.8", "934"),
            ("클렌징폼 150g", "18,000원", "4.5", "12,043"),
            ("마스크팩 10매", "22,000원", "4.7", "6,218"),
            ("에센스 50ml", "68,000원", "4.9", "2,105"),
            ("아이크림 20ml", "38,000원", "4.6", "1,876"),
            ("미스트 120ml", "19,000원", "4.5", "3,421"),
        ]
        return [
            NaverProduct(
                rank=i+1,
                name=f"{brand} {items[i%len(items)][0]}",
                brand=brand,
                price=items[i%len(items)][1],
                rating=items[i%len(items)][2],
                review_count=items[i%len(items)][3],
                category="뷰티",
                mall_name=f"{brand} 공식몰",
            )
            for i in range(n)
        ]
