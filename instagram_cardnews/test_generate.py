"""
test_generate.py — 목 데이터로 카드뉴스 생성 테스트 (API 키 불필요)
"""
import sys
sys.path.insert(0, ".")

from pathlib import Path
from scrapers.brand_info import BrandOverview, IngredientInfo
from scrapers.financial_data import FinancialSummary, PLStatement, InvestmentRound
from scrapers.olive_young import OliveYoungProduct
from scrapers.naver_smartstore import NaverProduct
from scrapers.amazon import AmazonProduct
from scrapers.tiktok import TikTokTrendData, TikTokHashtag
from scrapers.google_trends import TrendSummary, TrendPoint
from card_news.generator import CardNewsGenerator

# ── 목 데이터 구성 ──────────────────────────────────────────────────
brand_name = "라네즈"

brand_info = BrandOverview(
    name=brand_name,
    name_en="LANEIGE",
    category="스킨케어 / 색조",
    founded_year="1994년",
    founder="아모레퍼시픽",
    headquarters="서울특별시",
    website="laneige.com",
    description="라네즈는 아모레퍼시픽의 프리미엄 스킨케어 브랜드로, 수분 과학을 기반으로 한 제품으로 전 세계에서 사랑받고 있습니다.",
    key_products=["워터뱅크 세럼", "워터슬리핑마스크", "립슬리핑마스크"],
    tags=["스킨케어", "수분", "세럼", "마스크"],
    ingredients=[
        IngredientInfo(
            product_name="워터뱅크 블루히알루론 세럼",
            ingredients=["히알루론산", "나이아신아마이드", "판테놀", "세라마이드",
                         "글리세린", "부틸렌글라이콜", "수", "알로에베라",
                         "베타인", "스쿠알란", "레티놀", "펩타이드",
                         "비타민C", "아데노신", "EGF", "트레할로스",
                         "알란토인", "토코페롤"],
            source="화해"
        )
    ]
)

financial = FinancialSummary(
    brand_name=brand_name,
    pl_statements=[
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
    ],
    investment_rounds=[
        InvestmentRound("2019-03", "시리즈 A", "30억 원", ["IMM인베스트먼트"], "150억 원"),
        InvestmentRound("2020-09", "시리즈 B", "100억 원", ["한국투자파트너스", "카카오벤처스"], "500억 원"),
        InvestmentRound("2022-05", "시리즈 C", "300억 원", ["KKR", "스톤브릿지벤처스"], "2,000억 원"),
        InvestmentRound("2023-11", "Pre-IPO", "800억 원", ["블랙록", "미래에셋"], "8,000억 원"),
    ]
)

oy_products = [
    OliveYoungProduct(1, "라네즈 워터뱅크 세럼", "라네즈", "52,000원", "스킨케어", "4.9", "12,381"),
    OliveYoungProduct(2, "라네즈 립슬리핑마스크", "라네즈", "18,000원", "립케어", "4.8", "45,219"),
    OliveYoungProduct(5, "라네즈 선크림 SPF50+", "라네즈", "28,000원", "선케어", "4.7", "8,342"),
]

naver_products = [
    NaverProduct(1, "라네즈 워터뱅크 블루히알루론 세럼 60ml", "라네즈", "52,000원", "12,381", "4.9", "스킨케어", "라네즈 공식"),
    NaverProduct(2, "라네즈 워터슬리핑마스크 70ml", "라네즈", "23,000원", "28,142", "4.8"),
    NaverProduct(3, "라네즈 립슬리핑마스크 20g", "라네즈", "18,000원", "45,219", "4.8"),
]

amazon_products = [
    AmazonProduct(1, "B0001", "LANEIGE Lip Sleeping Mask", "LANEIGE", "$24.00", "4.7", "38,421", "Best Seller", marketplace="US"),
    AmazonProduct(2, "B0002", "LANEIGE Water Bank Hydro Essence", "LANEIGE", "$42.00", "4.6", "12,831", "", marketplace="US"),
    AmazonProduct(3, "B0003", "LANEIGE Neo Cushion", "LANEIGE", "$38.00", "4.5", "5,219", "", marketplace="US"),
]

tiktok = TikTokTrendData(
    brand_name=brand_name,
    hashtags=[
        TikTokHashtag("#라네즈", "245.8M", "↑상승"),
        TikTokHashtag("#laneige", "892.3M", "↑상승"),
        TikTokHashtag("#라네즈립슬리핑마스크", "134.2M", "↑상승"),
        TikTokHashtag("#kbeauty", "12.4B", "↑상승"),
    ],
    trend_score=85,
    virality="🔥 Viral",
)

trends = TrendSummary(
    brand_name=brand_name,
    monthly_trend=[
        TrendPoint("2024-01-01", 62), TrendPoint("2024-02-01", 68),
        TrendPoint("2024-03-01", 71), TrendPoint("2024-04-01", 75),
        TrendPoint("2024-05-01", 72), TrendPoint("2024-06-01", 78),
        TrendPoint("2024-07-01", 82), TrendPoint("2024-08-01", 85),
        TrendPoint("2024-09-01", 79), TrendPoint("2024-10-01", 88),
        TrendPoint("2024-11-01", 91), TrendPoint("2024-12-01", 95),
    ],
    related_queries=["라네즈 세럼", "라네즈 쿠션", "라네즈 후기", "라네즈 할인"],
    trend_direction="📈 상승",
    interest_score=95,
    peak_period="2024년 Q4",
)

# ── 카드뉴스 생성 ───────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  🎨  {brand_name} 카드뉴스 생성 테스트")
print(f"{'='*50}\n")

generator = CardNewsGenerator()
paths = generator.generate(
    brand=brand_info,
    financial=financial,
    oy_products=oy_products,
    naver_products=naver_products,
    amazon_products=amazon_products,
    tiktok=tiktok,
    trends=trends,
)

print(f"\n✅ 생성 완료! {len(paths)}장")
for p in paths:
    size_kb = p.stat().st_size // 1024
    print(f"   {p.name}  ({size_kb} KB)")
print(f"\n📁 저장 위치: {paths[0].parent}")
