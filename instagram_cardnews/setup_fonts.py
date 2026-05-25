"""
setup_fonts.py — 한글 폰트(NotoSansKR) 자동 다운로드 스크립트
실행: python setup_fonts.py
"""
import sys
import urllib.request
from pathlib import Path

FONTS_DIR = Path(__file__).parent / "fonts"
FONTS_DIR.mkdir(exist_ok=True)

FONTS = {
    "NotoSansKR-Regular.otf": (
        "https://raw.githubusercontent.com/googlefonts/noto-cjk/"
        "main/Sans/OTF/Korean/NotoSansCJKkr-Regular.otf"
    ),
    "NotoSansKR-Bold.otf": (
        "https://raw.githubusercontent.com/googlefonts/noto-cjk/"
        "main/Sans/OTF/Korean/NotoSansCJKkr-Bold.otf"
    ),
    "NotoSansKR-Light.otf": (
        "https://raw.githubusercontent.com/googlefonts/noto-cjk/"
        "main/Sans/OTF/Korean/NotoSansCJKkr-Light.otf"
    ),
}


def download(name: str, url: str):
    path = FONTS_DIR / name
    if path.exists():
        print(f"  ✓ 이미 있음: {name}")
        return
    print(f"  다운로드 중: {name} ...")
    try:
        urllib.request.urlretrieve(url, str(path))
        print(f"  ✓ 완료: {name} ({path.stat().st_size // 1024} KB)")
    except Exception as e:
        print(f"  ✗ 실패: {name} → {e}")


if __name__ == "__main__":
    print("NotoSansKR 폰트 다운로드\n")
    for name, url in FONTS.items():
        download(name, url)
    print("\n완료! fonts/ 디렉토리를 확인하세요.")
