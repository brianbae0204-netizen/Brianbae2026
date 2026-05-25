# 📸 Instagram 브랜드 카드뉴스 자동화 시스템

> **브랜드명 하나만 넣으면** — 전성분 · 재무 · 플랫폼 랭킹 · 트렌드를 자동 수집해서
> **인스타그램 카드뉴스 8장**을 만들고 **자동 포스팅**까지 합니다.

두 가지 레퍼런스 톤을 그대로 반영했습니다.
- **kodeok.kr** → 화이트 에디토리얼 톤&매너 (큰 볼드 제목 · 구분선 · 강조 본문 · 회색 콜아웃 · 하단 사진 · 페이지 점)
- **ekke.now** → 손익 **Sankey 자금흐름도** ("이렇게 벌고 쓴다")

---

## 🎨 두 가지 스타일

| 스타일 | 설명 | 규격 | 손익 차트 |
|--------|------|------|-----------|
| **editorial** (기본) | 화이트 에디토리얼, 큰 글씨, 사진 임베딩 | 1080×1350 (4:5) | **Sankey 흐름도** |
| dark (레거시) | 다크 네온 테마 | 1080×1080 (1:1) | 워터폴 차트 |

```bash
python main.py generate --brand "라네즈"                  # editorial (기본)
python main.py generate --brand "라네즈" --style dark      # 다크 테마
```

---

## 🗂️ 카드 구성 (8장 · editorial)

| # | 카드 | 내용 |
|---|------|------|
| 1 | 커버 | 히어로 사진 + 후킹 제목 |
| 2 | 브랜드 개요 | 설립·창업·정체성 스토리 |
| 3 | 핵심 성분 | 전성분 콜아웃 + 제품 사진 |
| 4 | 플랫폼 랭킹 | 올리브영·네이버·아마존 (대형 순위 숫자) |
| 5 | **손익 Sankey** | 매출→원가·판관비·이익 자금흐름도 + KPI |
| 6 | 투자유치 | 누적/기업가치 대형 숫자 + 라운드 타임라인 |
| 7 | 트렌드 | Google Trends · TikTok 화제성 |
| 8 | 종합 요약 | AI 인사이트 3줄 + 팔로우 CTA |

---

## 🏗️ 구조

```
instagram_cardnews/
├── main.py                       ← CLI (generate / post / schedule / history)
├── config.py                     ← EditorialTheme(화이트) · CardConfig(다크)
├── setup_fonts.py                ← NotoSansKR 폰트 다운로드
│
├── scrapers/                     ← 데이터 수집
│   ├── brand_info.py             네이버 API + 화해/올리브영 전성분
│   ├── financial_data.py         DART OpenAPI P&L + 투자이력
│   ├── olive_young.py            올리브영 랭킹
│   ├── naver_smartstore.py       네이버 쇼핑 순위
│   ├── amazon.py                 아마존 Best Sellers
│   ├── tiktok.py                 TikTok 해시태그 트렌드
│   └── google_trends.py          pytrends + 네이버 데이터랩
│
├── prompts/                      ← AI 카피라이팅 (kodeok.kr 톤)
│   └── copywriting.py            EditorialCopywriter · SYSTEM_PROMPT · 카드별 프롬프트
│
├── card_news/                    ← 카드뉴스 생성
│   ├── editorial_generator.py    화이트 에디토리얼 8장 (기본)
│   ├── editorial_templates.py    1080×1350 에디토리얼 템플릿 (**볼드** 인라인)
│   ├── sankey_chart.py           손익 Sankey 흐름도 (matplotlib 베지어)
│   ├── generator.py              다크 테마 8장 (레거시)
│   ├── card_templates.py         다크 템플릿
│   └── waterfall_chart.py        워터폴 차트
│
├── instagram/                    ← 자동화
│   ├── client.py                 instagrapi Carousel 업로드
│   └── scheduler.py              APScheduler 예약/자동 포스팅
│
└── utils/
    ├── image_utils.py            폰트·그라디언트·라운드 박스
    ├── image_fetch.py            사진 다운로드·크롭·스트립·플레이스홀더
    └── text_utils.py             텍스트·캡션 생성
```

---

## ⚡ 빠른 시작

```bash
pip install -r requirements.txt
python setup_fonts.py            # 한글 폰트
cp .env.example .env             # API 키 입력 (선택)

python main.py generate --brand "라네즈"      # 카드뉴스 생성
python main.py post     --brand "라네즈" --now # 생성 + 즉시 포스팅
python main.py schedule --brands "라네즈,이니스프리" --times "09:00,18:00"
```

> API 키 없이도 **목 데이터 + 규칙기반 카피**로 8장이 완성됩니다.
> `ANTHROPIC_API_KEY`를 넣으면 카피가 AI 에디토리얼 톤으로 업그레이드됩니다.

---

## 🤖 AI 카피라이팅 (prompts/copywriting.py)

`SYSTEM_PROMPT`가 kodeok.kr 톤&매너를 규정합니다.

- 짧고 강한 후킹 제목 ("결혼이 미뤄지자, 돈이 남았다" 류)
- 구어체 본문 + `**별표**` 강조
- 업계 용어 1개를 정의와 함께 ("위에지(悦己) 경제")
- 과장·이모지 금지 → JSON 구조로 반환

```python
from prompts import EditorialCopywriter
copy = EditorialCopywriter().write("pl", "라네즈", {"revenue": 1850, "operating_margin": 31.9})
# CardCopy(kicker, title, body[], callout[], closing, big_number, ...)
```

---

## 📊 손익 Sankey (card_news/sankey_chart.py)

ekke.now 스타일 자금흐름도. 흑자/적자(순손실) 모두 지원.

```
총 매출 ─┬─→ 매출원가
         ├─→ 판관비 ─→ 인건비/광고선전비/운영관리비/감가상각비/기타
         └─→ 영업이익 ─→ 법인세 / 순이익
```

판관비 세부는 화장품 업계 평균 비율로 추정 분해하며,
라벨이 겹치지 않도록 우측 항목을 단일 세로 스택으로 균등 배치합니다.

---

## 🔑 API 키 (모두 선택)

| API | 발급처 | 비용 |
|-----|--------|------|
| DART | opendart.fss.or.kr | 무료 |
| 네이버 검색/쇼핑/데이터랩 | developers.naver.com | 무료 |
| Anthropic Claude | console.anthropic.com | 유료 |

---

## ⚠️ 주의

- Instagram 비공식 API(instagrapi) → 과도한 자동화 시 계정 제재 가능, 하루 2~3회 권장
- 웹 스크래핑은 각 사이트 약관 확인 필요
