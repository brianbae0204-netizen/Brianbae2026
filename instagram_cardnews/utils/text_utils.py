"""
text_utils.py — 텍스트 처리 유틸리티
"""
from __future__ import annotations

import re
from typing import List


def truncate(text: str, max_len: int = 30, ellipsis: str = "...") -> str:
    """문자열 자르기"""
    if len(text) <= max_len:
        return text
    return text[:max_len - len(ellipsis)] + ellipsis


def wrap_text(text: str, max_chars: int = 20) -> List[str]:
    """긴 문자열 줄 나누기"""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def clean_html(text: str) -> str:
    """HTML 태그 제거"""
    clean = re.compile(r"<.*?>")
    return re.sub(clean, "", text).strip()


def format_number_ko(n: float) -> str:
    """숫자를 한국식 표기로 변환 (1234 → 1,234 / 100000000 → 1억)"""
    if n >= 1e12:
        return f"{n/1e12:.1f}조"
    elif n >= 1e8:
        return f"{n/1e8:.1f}억"
    elif n >= 1e4:
        return f"{n/1e4:.1f}만"
    else:
        return f"{n:,.0f}"


def extract_hashtags(text: str) -> List[str]:
    """텍스트에서 해시태그 추출"""
    return re.findall(r"#\w+", text)


def build_instagram_caption(
    brand_name: str,
    summary: str,
    hashtags: List[str],
    emojis: bool = True,
) -> str:
    """인스타그램 캡션 생성"""
    lines = [
        f"{'📊 ' if emojis else ''}{brand_name} 브랜드 분석 리포트",
        "",
        summary,
        "",
        "─" * 25,
        "",
    ]
    lines += [f"#{tag.lstrip('#')}" for tag in hashtags[:30]]
    lines += [
        "",
        "#브랜드분석 #뷰티트렌드 #카드뉴스 #투자 #인플루언서 #kbeauty"
    ]
    return "\n".join(lines)
