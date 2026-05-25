"""
client.py — Instagram 자동 포스팅 클라이언트
  • instagrapi 라이브러리 사용 (비공개 API)
  • 카드뉴스 (Carousel/Album) 업로드
  • 세션 저장/복원으로 반복 로그인 최소화
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional

from loguru import logger

try:
    from instagrapi import Client
    from instagrapi.exceptions import (
        LoginRequired,
        TwoFactorRequired,
        BadPassword,
        ChallengeRequired,
    )
    INSTAGRAPI_OK = True
except ImportError:
    INSTAGRAPI_OK = False
    logger.warning("instagrapi 미설치 → Instagram 업로드 비활성화")

from config import InstagramConfig, OUTPUT_DIR


SESSION_FILE = OUTPUT_DIR / "ig_session.json"


class InstagramClient:
    """Instagram 카드뉴스 업로드 클라이언트"""

    def __init__(self,
                 username: str = "",
                 password: str = ""):
        self.username = username or InstagramConfig.USERNAME
        self.password = password or InstagramConfig.PASSWORD
        self._client: Optional["Client"] = None

    # ──────────────────────────────────────────────────────────────
    # 로그인
    # ──────────────────────────────────────────────────────────────
    def login(self) -> bool:
        if not INSTAGRAPI_OK:
            logger.error("instagrapi 미설치")
            return False
        if not self.username or not self.password:
            logger.error("Instagram 계정 정보 없음 (.env 파일 확인)")
            return False

        self._client = Client()
        self._client.delay_range = [2, 5]   # 요청 간 딜레이 (봇 방지)

        # 저장된 세션 복원
        if SESSION_FILE.exists():
            try:
                self._client.load_settings(str(SESSION_FILE))
                self._client.login(self.username, self.password)
                logger.success("세션 복원 성공")
                return True
            except LoginRequired:
                logger.info("세션 만료 → 재로그인")
            except Exception as e:
                logger.warning(f"세션 복원 실패: {e}")

        # 신규 로그인
        try:
            self._client.login(self.username, self.password)
            self._client.dump_settings(str(SESSION_FILE))
            logger.success(f"Instagram 로그인 성공: @{self.username}")
            return True
        except TwoFactorRequired:
            code = input("2FA 인증 코드 입력: ").strip()
            try:
                self._client.login(self.username, self.password,
                                    verification_code=code)
                self._client.dump_settings(str(SESSION_FILE))
                return True
            except Exception as e:
                logger.error(f"2FA 로그인 실패: {e}")
                return False
        except BadPassword:
            logger.error("비밀번호 오류")
            return False
        except ChallengeRequired:
            logger.error("Instagram 챌린지 인증 필요 → 앱에서 직접 확인")
            return False
        except Exception as e:
            logger.error(f"로그인 실패: {e}")
            return False

    # ──────────────────────────────────────────────────────────────
    # 카드뉴스 (Carousel) 업로드
    # ──────────────────────────────────────────────────────────────
    def upload_carousel(
        self,
        image_paths: List[Path],
        caption:     str,
        location:    Optional[str] = None,
    ) -> Optional[str]:
        """
        여러 이미지를 carousel(앨범) 형식으로 업로드
        Returns: 업로드된 media_id 또는 None
        """
        if not INSTAGRAPI_OK:
            logger.warning("[DRY-RUN] instagrapi 없음 → 업로드 건너뜀")
            return None
        if not self._client:
            if not self.login():
                return None

        # 이미지 경로 → 문자열 변환
        paths = [str(p) for p in image_paths if Path(p).exists()]
        if not paths:
            logger.error("업로드할 이미지 없음")
            return None

        logger.info(f"Instagram 업로드 시작 ({len(paths)}장) ...")
        try:
            if len(paths) == 1:
                media = self._client.photo_upload(paths[0], caption)
            else:
                media = self._client.album_upload(paths, caption)
            media_id = media.pk
            logger.success(f"✅ 업로드 완료! media_id={media_id}")
            logger.info(f"   → https://www.instagram.com/p/{media.code}/")
            return str(media_id)
        except LoginRequired:
            logger.warning("세션 만료 → 재로그인 후 재시도")
            if self.login():
                return self.upload_carousel(image_paths, caption, location)
        except Exception as e:
            logger.error(f"업로드 실패: {e}")
        return None

    # ──────────────────────────────────────────────────────────────
    # 단일 이미지 업로드
    # ──────────────────────────────────────────────────────────────
    def upload_photo(self, image_path: Path, caption: str) -> Optional[str]:
        return self.upload_carousel([image_path], caption)

    # ──────────────────────────────────────────────────────────────
    # 계정 정보 조회
    # ──────────────────────────────────────────────────────────────
    def get_account_info(self) -> dict:
        if not self._client:
            return {}
        try:
            user = self._client.account_info()
            return {
                "username":    user.username,
                "full_name":   user.full_name,
                "followers":   user.follower_count,
                "following":   user.following_count,
                "posts":       user.media_count,
                "bio":         user.biography,
                "is_business": user.is_business,
            }
        except Exception as e:
            logger.warning(f"계정 정보 조회 실패: {e}")
            return {}

    def logout(self):
        if self._client:
            try:
                self._client.logout()
                logger.info("Instagram 로그아웃 완료")
            except Exception:
                pass
