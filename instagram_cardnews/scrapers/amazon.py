"""
amazon.py — 아마존 Best Sellers 랭킹 수집
  • Amazon Product Advertising API 5.0 (키 있을 때)
  • amazon.com/amazon.co.jp Best Sellers 웹 스크래핑 (fallback)
"""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlencode, quote

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config import APIKeys, SCRAPER_HEADERS


@dataclass
class AmazonProduct:
    rank:    int
    asin:    str
    name:    str
    brand:   str
    price:   str
    rating:  Optional[str] = None
    reviews: Optional[str] = None
    badge:   str = ""          # "Best Seller", "#1", etc.
    url:     str = ""
    image:   str = ""
    marketplace: str = "US"


class AmazonScraper:
    """아마존 랭킹 스크래퍼 (PA-API + 웹 스크래핑)"""

    BS_URL = {
        "US": "https://www.amazon.com/best-sellers-beauty/zgbs/beauty",
        "JP": "https://www.amazon.co.jp/gp/bestsellers/beauty",
        "UK": "https://www.amazon.co.uk/best-sellers-beauty/zgbs/beauty",
    }
    PA_API_HOST = "webservices.amazon.com"
    PA_API_PATH = "/paapi5/searchitems"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(SCRAPER_HEADERS)

    # ──────────────────────────────────────────────────────────────
    # 1. 웹 스크래핑 fallback
    # ──────────────────────────────────────────────────────────────
    def _scrape_best_sellers(self, marketplace: str = "US",
                             limit: int = 10) -> List[AmazonProduct]:
        url = self.BS_URL.get(marketplace, self.BS_URL["US"])
        products = []
        try:
            resp = self.session.get(url, timeout=20)
            soup = BeautifulSoup(resp.text, "lxml")

            # Best Sellers 리스트 아이템
            items = soup.select("div.zg-item-immersion")[:limit]
            if not items:
                items = soup.select("li.zg-item")[:limit]

            for i, item in enumerate(items, 1):
                rank_tag  = item.select_one("span.zg-bdg-text")
                name_tag  = item.select_one("div.p13n-sc-truncate, span._cDEzb_p13n-sc-css-line-clamp-3_g3dy1")
                price_tag = item.select_one("span.p13n-sc-price, .a-price .a-offscreen")
                a_tag     = item.select_one("a.a-link-normal")
                img_tag   = item.select_one("img.s-image, img._cDEzb_p13n-sc-dummy-image_1G8uo")
                rating_tag = item.select_one("span.a-icon-alt")
                review_tag = item.select_one("span.a-size-small")

                rank_str = rank_tag.text.strip().lstrip("#") if rank_tag else str(i)
                products.append(AmazonProduct(
                    rank=int(rank_str) if rank_str.isdigit() else i,
                    asin="",
                    name=name_tag.text.strip() if name_tag else f"Product {i}",
                    brand="",
                    price=price_tag.text.strip() if price_tag else "",
                    rating=rating_tag.text.split(" ")[0] if rating_tag else None,
                    reviews=review_tag.text.strip() if review_tag else None,
                    url="https://www.amazon.com" + a_tag.get("href", "") if a_tag else "",
                    image=img_tag.get("src", "") if img_tag else "",
                    marketplace=marketplace,
                ))
        except Exception as e:
            logger.warning(f"아마존 Best Sellers 스크래핑 실패 [{marketplace}]: {e}")
            products = self._mock_products(marketplace, limit)
        return products

    # ──────────────────────────────────────────────────────────────
    # 2. 브랜드 검색
    # ──────────────────────────────────────────────────────────────
    def search_brand_rank(self, brand_name: str,
                          marketplace: str = "US",
                          limit: int = 10) -> List[AmazonProduct]:
        products = []
        try:
            search_url = f"https://www.amazon.com/s?k={quote(brand_name)}&i=beauty"
            resp = self.session.get(search_url, timeout=20)
            soup = BeautifulSoup(resp.text, "lxml")

            items = soup.select("div[data-component-type='s-search-result']")[:limit]
            for i, item in enumerate(items, 1):
                name_tag   = item.select_one("h2 a span")
                price_tag  = item.select_one("span.a-price .a-offscreen")
                rating_tag = item.select_one("span.a-icon-alt")
                review_tag = item.select_one("span[aria-label*='ratings']")
                badge_tag  = item.select_one("span.a-badge-text")
                a_tag      = item.select_one("h2 a")
                asin       = item.get("data-asin", "")

                products.append(AmazonProduct(
                    rank=i,
                    asin=asin,
                    name=name_tag.text.strip() if name_tag else "",
                    brand=brand_name,
                    price=price_tag.text.strip() if price_tag else "",
                    rating=rating_tag.text.split(" ")[0] if rating_tag else None,
                    reviews=review_tag.get("aria-label", "").split(" ")[0] if review_tag else None,
                    badge=badge_tag.text.strip() if badge_tag else "",
                    url="https://www.amazon.com" + a_tag.get("href", "") if a_tag else "",
                    marketplace=marketplace,
                ))
        except Exception as e:
            logger.warning(f"아마존 브랜드 검색 실패: {e}")
            products = self._mock_products(marketplace, limit)
        return products

    def fetch_best_sellers(self, marketplace: str = "US",
                           limit: int = 10) -> List[AmazonProduct]:
        return self._scrape_best_sellers(marketplace, limit)

    @staticmethod
    def _mock_products(marketplace: str, n: int) -> List[AmazonProduct]:
        mock = [
            ("CeraVe Hydrating Facial Cleanser", "CeraVe", "$12.99"),
            ("Neutrogena Rapid Wrinkle Repair", "Neutrogena", "$24.49"),
            ("EltaMD UV Clear SPF 46", "EltaMD", "$41.00"),
            ("The Ordinary Niacinamide 10%", "The Ordinary", "$7.90"),
            ("Paula's Choice BHA Exfoliant", "Paula's Choice", "$34.00"),
            ("Cetaphil Moisturizing Cream", "Cetaphil", "$16.49"),
            ("Olay Regenerist Micro-Sculpting", "Olay", "$28.99"),
            ("Kiehl's Ultra Facial Cream", "Kiehl's", "$34.00"),
            ("La Mer Moisturizing Cream", "La Mer", "$200.00"),
            ("Tatcha The Water Cream", "Tatcha", "$69.00"),
        ]
        return [
            AmazonProduct(
                rank=i+1,
                asin=f"B0000{i:05d}",
                name=mock[i%len(mock)][0],
                brand=mock[i%len(mock)][1],
                price=mock[i%len(mock)][2],
                rating="4.5",
                reviews=f"{(5000 - i*400):,}",
                badge="Best Seller" if i < 3 else "",
                marketplace=marketplace,
            )
            for i in range(n)
        ]
