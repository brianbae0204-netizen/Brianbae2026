"""
test_editorial.py — 화이트 에디토리얼 + Sankey 카드뉴스 생성 테스트 (목 데이터)
"""
import sys
sys.path.insert(0, ".")

from scrapers.brand_info import BrandOverview, IngredientInfo
from scrapers.financial_data import FinancialSummary, PLStatement, InvestmentRound
from scrapers.olive_young import OliveYoungProduct
from scrapers.naver_smartstore import NaverProduct
from scrapers.amazon import AmazonProduct
from scrapers.tiktok import TikTokTrendData, TikTokHashtag
from scrapers.google_trends import TrendSummary, TrendPoint
from card_news.editorial_generator import EditorialCardNewsGenerator

brand_name = "라네즈"

brand_info = BrandOverview(
    name=brand_name, name_en="LANEIGE", category="스킨케어 / 색조",
    founded_year="1994년", founder="아모레퍼시픽", headquarters="서울",
    website="laneige.com",
    description="수분 과학 기반 프리미엄 스킨케어 브랜드.",
    key_products=["워터뱅크 세럼", "립슬리핑마스크", "워터슬리핑마스크"],
    tags=["스킨케어", "수분", "세럼"],
    ingredients=[IngredientInfo(
        product_name="워터뱅크 블루히알루론 세럼",
        ingredients=["히알루론산", "나이아신아마이드", "판테놀", "세라마이드",
                     "펩타이드", "비타민C"],
        source="화해")],
)

financial = FinancialSummary(
    brand_name=brand_name,
    pl_statements=[PLStatement(
        year=2023, revenue=1850.0, cogs=740.0, gross_profit=1110.0,
        selling_expenses=520.0, operating_income=590.0, ebitda=680.0,
        interest_expense=18.0, tax=145.0, net_income=427.0,
        gross_margin=60.0, operating_margin=31.9, net_margin=23.1)],
    investment_rounds=[
        InvestmentRound("2019-03", "시리즈 A", "30억 원", ["IMM인베스트먼트"], "150억 원"),
        InvestmentRound("2020-09", "시리즈 B", "100억 원", ["카카오벤처스"], "500억 원"),
        InvestmentRound("2022-05", "시리즈 C", "300억 원", ["KKR"], "2,000억 원"),
        InvestmentRound("2023-11", "Pre-IPO", "800억 원", ["블랙록"], "8,000억 원"),
    ],
)

oy = [OliveYoungProduct(1, "라네즈 워터뱅크 세럼", "라네즈", "52,000원", "스킨케어", "4.9", "12,381"),
      OliveYoungProduct(2, "라네즈 립슬리핑마스크", "라네즈", "18,000원", "립케어", "4.8", "45,219")]
naver = [NaverProduct(1, "라네즈 워터뱅크 세럼 60ml", "라네즈", "52,000원", "12,381", "4.9"),
         NaverProduct(3, "라네즈 립슬리핑마스크", "라네즈", "18,000원", "45,219", "4.8")]
amazon = [AmazonProduct(1, "B01", "LANEIGE Lip Sleeping Mask", "LANEIGE", "$24", "4.7", "38,421", "Best Seller")]

tiktok = TikTokTrendData(brand_name=brand_name, hashtags=[
    TikTokHashtag("#laneige", "892.3M", "↑상승"),
    TikTokHashtag("#라네즈", "245.8M", "↑상승")],
    trend_score=85, virality="Viral")

trends = TrendSummary(brand_name=brand_name,
    monthly_trend=[TrendPoint(f"2024-{m:02d}-01", 60 + m * 3) for m in range(1, 13)],
    related_queries=["라네즈 세럼", "라네즈 쿠션", "라네즈 후기"],
    trend_direction="상승", interest_score=95, peak_period="2024 Q4")

print("\n" + "=" * 50)
print(f"  화이트 에디토리얼 + Sankey 카드뉴스 테스트: {brand_name}")
print("=" * 50 + "\n")

gen = EditorialCardNewsGenerator()
paths = gen.generate(brand_info, financial, oy, naver, amazon, tiktok, trends)

print(f"\n생성 완료: {len(paths)}장")
for p in paths:
    print(f"  {p.name}  ({p.stat().st_size // 1024} KB)")
print(f"\n저장 위치: {paths[0].parent}")
