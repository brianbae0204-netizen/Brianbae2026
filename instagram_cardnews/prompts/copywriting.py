"""
copywriting.py — 에디토리얼 카드뉴스 AI 카피라이팅
  • kodeok.kr 톤&매너: 짧고 강한 후킹 제목 + 인사이트 본문 + 콜아웃
  • Claude API로 카드별 카피 생성, JSON 구조로 반환
  • API 키 없으면 규칙 기반(템플릿) 카피로 폴백
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from loguru import logger

from config import APIKeys

try:
    import anthropic
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False


# ══════════════════════════════════════════════════════════════════════
# 카드 카피 데이터 모델
# ══════════════════════════════════════════════════════════════════════
@dataclass
class CardCopy:
    kicker:   str = ""              # 제목 위 작은 라벨 (예: "BRAND OVERVIEW")
    title:    str = ""              # 큰 후킹 제목 (1~2줄)
    body:     List[str] = field(default_factory=list)   # 본문 줄들 (**볼드** 마크업 허용)
    callout:  List[str] = field(default_factory=list)   # 회색 콜아웃 박스 줄들
    closing:  str = ""             # 마무리 한 문장
    big_number: str = ""           # 초대형 강조 숫자 (선택)
    big_number_label: str = ""     # 숫자 설명


# ══════════════════════════════════════════════════════════════════════
# 시스템 프롬프트 — 에디토리얼 톤&매너 정의
# ══════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """\
당신은 한국 인스타그램에서 화제가 되는 '브랜드 분석 카드뉴스'를 만드는
시니어 에디터입니다. 당신의 글은 다음 레퍼런스 톤&매너를 따릅니다.

[톤 & 매너 — 반드시 준수]
1. 제목은 짧고 강력한 후킹형. 호기심·반전·통찰을 담는다.
   - 좋은 예: "결혼이 미뤄지자, 돈이 남았다"
   - 좋은 예: "이 브랜드는 이렇게 벌고 쓴다"
   - 나쁜 예: "OO 브랜드 개요" (밋밋함, 금지)
2. 본문은 구어체 ("~거든요", "~이에요", "~죠"). 한 문장은 짧게.
3. 핵심 숫자·키워드는 **별표**로 감싸 강조한다. 예: **1억 2천만 명**
4. 전문용어는 쉽게 풀되, 업계 용어 1개 정도는 '정의'와 함께 던진다.
   예: "시장은 이걸 '위에지(悦己) 경제'라고 불러요."
5. 과장·홍보 금지. 데이터에 근거한 담백한 인사이트.
6. 이모지는 쓰지 않는다 (텍스트는 깔끔하게). 기호 ✓ ✗ → 만 콜아웃에 허용.

[출력 형식 — 반드시 JSON만 출력]
{
  "kicker": "영문 대문자 라벨 (예: BRAND OVERVIEW)",
  "title": "후킹 제목 (최대 2줄, \\n으로 줄바꿈, 한 줄 16자 내외)",
  "body": ["본문 문장1", "본문 문장2", "..."],
  "callout": ["콜아웃 줄1", "콜아웃 줄2"],
  "closing": "마무리 한 문장",
  "big_number": "초대형 숫자 (선택, 없으면 빈 문자열)",
  "big_number_label": "숫자 설명 (선택)"
}

[제약]
- title: 한 줄 16자 이내, 최대 2줄
- body: 2~4문장, 각 문장 28자 이내
- callout: 1~3줄, 각 줄 24자 이내
- 반드시 위 JSON 스키마만 출력. 설명·마크다운 코드펜스 금지.
"""


# ══════════════════════════════════════════════════════════════════════
# 카드별 프롬프트 빌더
# ══════════════════════════════════════════════════════════════════════
def build_card_prompt(card_type: str, brand_name: str, data: Dict) -> str:
    """카드 종류별 사용자 프롬프트 생성"""
    ctx = json.dumps(data, ensure_ascii=False, indent=2)

    instructions = {
        "cover": (
            f"'{brand_name}' 브랜드 분석 카드뉴스의 **표지(커버)** 카피를 써줘. "
            f"보는 순간 스와이프하고 싶게 만드는 강력한 한 줄 후킹 제목이 핵심. "
            f"body는 1문장, callout은 비워도 됨."
        ),
        "overview": (
            f"'{brand_name}'의 **브랜드 개요** 카드. 설립·창업·정체성을 "
            f"흥미로운 스토리로. 설립연도/창업자/카테고리를 본문에 녹여줘."
        ),
        "ingredients": (
            f"'{brand_name}'의 **핵심 성분/제품력** 카드. 어떤 성분이 왜 강점인지 "
            f"소비자 관점에서. callout에 핵심 성분 3~5개를 '→' 기호로 정리."
        ),
        "ranking": (
            f"'{brand_name}'의 **플랫폼 랭킹** 카드. 올리브영·네이버·아마존 순위를 "
            f"근거로 시장 장악력을 보여줘. big_number에 대표 순위(예: '#1')."
        ),
        "pl": (
            f"'{brand_name}'의 **손익 구조** 카드. 매출·원가·이익 흐름을 한 문장으로 "
            f"통찰력 있게. '이렇게 벌고 쓴다' 류의 제목. 숫자는 본문에 녹여줘."
        ),
        "investment": (
            f"'{brand_name}'의 **투자유치 이력** 카드. 라운드별 성장 서사를. "
            f"big_number에 누적 투자금 또는 최신 기업가치."
        ),
        "trend": (
            f"'{brand_name}'의 **트렌드/화제성** 카드. Google Trends·TikTok 데이터로 "
            f"지금 왜 뜨는지. big_number에 트렌드 지수 또는 조회수."
        ),
        "summary": (
            f"'{brand_name}' 분석의 **종합 요약** 카드. 3가지 핵심 인사이트를 "
            f"날카롭게. closing에 팔로우 유도 CTA를 자연스럽게."
        ),
    }
    inst = instructions.get(card_type, f"'{brand_name}' 카드 카피를 써줘.")
    return f"{inst}\n\n[수집 데이터]\n{ctx}"


# ══════════════════════════════════════════════════════════════════════
# 카피라이터
# ══════════════════════════════════════════════════════════════════════
class EditorialCopywriter:
    def __init__(self, model: str = "claude-opus-4-7"):
        self.model = model
        self.client = (
            anthropic.Anthropic(api_key=APIKeys.ANTHROPIC)
            if (ANTHROPIC_OK and APIKeys.ANTHROPIC) else None
        )
        if not self.client:
            logger.info("[Copywriter] Anthropic 키 없음 → 템플릿 카피 사용")

    # ──────────────────────────────────────────────────────────────
    def write(self, card_type: str, brand_name: str, data: Dict) -> CardCopy:
        if self.client:
            copy = self._ai_write(card_type, brand_name, data)
            if copy:
                return copy
        return self._fallback(card_type, brand_name, data)

    # ──────────────────────────────────────────────────────────────
    def _ai_write(self, card_type: str, brand_name: str,
                  data: Dict) -> Optional[CardCopy]:
        try:
            msg = self.client.messages.create(
                model=self.model,
                max_tokens=700,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": build_card_prompt(card_type, brand_name, data),
                }],
            )
            raw = msg.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
            obj = json.loads(raw)
            return CardCopy(
                kicker=obj.get("kicker", ""),
                title=obj.get("title", ""),
                body=obj.get("body", []),
                callout=obj.get("callout", []),
                closing=obj.get("closing", ""),
                big_number=obj.get("big_number", ""),
                big_number_label=obj.get("big_number_label", ""),
            )
        except Exception as e:
            logger.warning(f"[Copywriter] AI 카피 실패 ({card_type}): {e}")
            return None

    # ──────────────────────────────────────────────────────────────
    # 규칙 기반 폴백 (API 없이도 에디토리얼 느낌 유지)
    # ──────────────────────────────────────────────────────────────
    def _fallback(self, card_type: str, brand_name: str,
                  data: Dict) -> CardCopy:
        b = brand_name
        if card_type == "cover":
            return CardCopy(
                kicker="BRAND DEEP DIVE",
                title=f"{b}는\n이렇게 큰다",
                body=[f"성분부터 재무, 랭킹까지", "데이터로 뜯어봤어요."],
                closing="→ 넘겨서 확인하세요",
            )
        if card_type == "overview":
            yr = data.get("founded_year", "")
            cat = data.get("category", "")
            founder = data.get("founder", "")
            body = []
            if yr:
                body.append(f"**{yr}** 시작된 브랜드예요.")
            if founder:
                body.append(f"창업자는 **{founder}**.")
            if cat:
                body.append(f"카테고리는 {cat}.")
            if not body:
                body = [f"{b}의 시작을 들여다봤어요."]
            return CardCopy(
                kicker="BRAND OVERVIEW",
                title=f"{b},\n어떻게 시작됐나",
                body=body,
                callout=[f"한 줄 요약", f"→ {cat or '뷰티'} 카테고리 강자"],
            )
        if card_type == "ingredients":
            ings = data.get("ingredients", [])[:5]
            return CardCopy(
                kicker="WHAT'S INSIDE",
                title="성분표가\n말해주는 것",
                body=["좋은 성분이 곧 신뢰예요.", "핵심만 골라봤어요."],
                callout=[f"→ {i}" for i in ings] or ["→ 데이터 수집 중"],
            )
        if card_type == "ranking":
            top = data.get("top_rank", "#1")
            return CardCopy(
                kicker="MARKET POSITION",
                title="숫자가 증명하는\n시장 장악력",
                body=["올리브영·네이버·아마존,", "어디서든 상위권이에요."],
                big_number=str(top),
                big_number_label="대표 플랫폼 최고 순위",
            )
        if card_type == "pl":
            rev = data.get("revenue", "")
            opm = data.get("operating_margin", "")
            body = []
            if rev:
                body.append(f"매출 **{rev}억**,")
            if opm:
                body.append(f"영업이익률 **{opm}%**.")
            body.append("돈의 흐름을 그려봤어요.")
            return CardCopy(
                kicker="HOW THEY EARN & SPEND",
                title=f"{b}는\n이렇게 벌고 쓴다",
                body=body,
                closing="아래 흐름도로 한눈에",
            )
        if card_type == "investment":
            total = data.get("total_funding", "")
            val = data.get("valuation", "")
            return CardCopy(
                kicker="FUNDING HISTORY",
                title="투자자들이\n베팅한 이유",
                body=["라운드마다 몸값이 뛰었어요.", "성장 서사를 정리했어요."],
                big_number=val or total or "",
                big_number_label="최신 기업가치" if val else "누적 투자유치",
            )
        if card_type == "trend":
            score = data.get("trend_score", "")
            views = data.get("tiktok_views", "")
            return CardCopy(
                kicker="WHY IT'S HOT NOW",
                title="지금 왜\n뜨는 걸까",
                body=["검색량도, 틱톡도 우상향.", "화제성을 수치로 봤어요."],
                big_number=views or (f"{score}/100" if score else ""),
                big_number_label="TikTok 누적 조회수" if views else "트렌드 지수",
            )
        if card_type == "summary":
            return CardCopy(
                kicker="THE BOTTOM LINE",
                title="결국,\n무엇이 남나",
                body=["성분·재무·화제성 모두 합격점.",
                      "기록해 둘 브랜드예요."],
                callout=["3줄 요약", "→ 제품력 탄탄", "→ 수익성 우수", "→ 화제성 상승"],
                closing="팔로우하고 다음 분석도 받아보세요",
            )
        return CardCopy(title=b)
