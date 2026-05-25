"""
scheduler.py — 인스타그램 자동 포스팅 스케줄러
  • APScheduler 기반
  • 예약 포스팅 / 큐 관리
  • 포스팅 이력 JSON 저장
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from loguru import logger

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_OK = True
except ImportError:
    APSCHEDULER_OK = False
    logger.warning("APScheduler 미설치 → 스케줄링 비활성화")

from config import OUTPUT_DIR, SchedulerConfig
from instagram.client import InstagramClient


HISTORY_FILE = OUTPUT_DIR / "post_history.json"


@dataclass
class PostJob:
    brand_name:   str
    image_paths:  List[str]
    caption:      str
    scheduled_at: str         # ISO datetime string
    status:       str = "pending"  # pending / done / failed
    media_id:     str = ""
    posted_at:    str = ""
    error:        str = ""


class PostScheduler:
    """자동 포스팅 스케줄러"""

    def __init__(self, ig_client: Optional[InstagramClient] = None):
        self.client = ig_client or InstagramClient()
        self._scheduler = BackgroundScheduler(timezone=SchedulerConfig.TIMEZONE) \
            if APSCHEDULER_OK else None
        self._queue: List[PostJob] = []
        self._history: List[PostJob] = self._load_history()

    # ──────────────────────────────────────────────────────────────
    # 이력 관리
    # ──────────────────────────────────────────────────────────────
    def _load_history(self) -> List[PostJob]:
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return [PostJob(**item) for item in json.load(f)]
            except Exception:
                pass
        return []

    def _save_history(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([asdict(j) for j in self._history], f,
                      ensure_ascii=False, indent=2)

    # ──────────────────────────────────────────────────────────────
    # 큐에 추가
    # ──────────────────────────────────────────────────────────────
    def enqueue(
        self,
        brand_name:  str,
        image_paths: List[Path],
        caption:     str,
        scheduled_at: Optional[datetime] = None,
    ) -> PostJob:
        job = PostJob(
            brand_name=brand_name,
            image_paths=[str(p) for p in image_paths],
            caption=caption,
            scheduled_at=(scheduled_at or datetime.now()).isoformat(),
        )
        self._queue.append(job)
        logger.info(f"[Scheduler] 큐 추가: {brand_name} "
                    f"(예약: {job.scheduled_at})")
        return job

    # ──────────────────────────────────────────────────────────────
    # 즉시 포스팅
    # ──────────────────────────────────────────────────────────────
    def post_now(
        self,
        brand_name:  str,
        image_paths: List[Path],
        caption:     str,
    ) -> PostJob:
        job = PostJob(
            brand_name=brand_name,
            image_paths=[str(p) for p in image_paths],
            caption=caption,
            scheduled_at=datetime.now().isoformat(),
        )
        self._execute_job(job)
        return job

    # ──────────────────────────────────────────────────────────────
    # 큐 처리
    # ──────────────────────────────────────────────────────────────
    def process_queue(self):
        """대기 중인 작업 모두 처리"""
        now = datetime.now()
        pending = [j for j in self._queue if j.status == "pending"]
        logger.info(f"[Scheduler] 큐 처리 시작 ({len(pending)}개)")
        for job in pending:
            scheduled = datetime.fromisoformat(job.scheduled_at)
            if scheduled <= now:
                self._execute_job(job)
                time.sleep(3)  # 연속 업로드 간 딜레이

    def _execute_job(self, job: PostJob):
        paths = [Path(p) for p in job.image_paths]
        media_id = self.client.upload_carousel(paths, job.caption)
        if media_id:
            job.status   = "done"
            job.media_id = media_id
            job.posted_at = datetime.now().isoformat()
            logger.success(f"[Scheduler] ✅ 포스팅 완료: {job.brand_name}")
        else:
            job.status = "failed"
            job.error  = "업로드 실패"
            logger.error(f"[Scheduler] ❌ 포스팅 실패: {job.brand_name}")
        self._history.append(job)
        self._save_history()
        if job in self._queue:
            self._queue.remove(job)

    # ──────────────────────────────────────────────────────────────
    # APScheduler 기반 자동 스케줄링
    # ──────────────────────────────────────────────────────────────
    def start_auto_schedule(
        self,
        callback: Callable,
        post_times: Optional[List[str]] = None,
    ):
        """
        매일 지정 시간에 callback 실행
        callback: () → (brand_name, image_paths, caption)
        """
        if not self._scheduler:
            logger.error("APScheduler 미설치")
            return
        times = post_times or SchedulerConfig.POST_TIMES
        for t in times:
            hour, minute = map(int, t.split(":"))
            self._scheduler.add_job(
                func=self._auto_post_wrapper,
                trigger=CronTrigger(hour=hour, minute=minute,
                                    timezone=SchedulerConfig.TIMEZONE),
                args=[callback],
                id=f"auto_post_{t}",
                replace_existing=True,
            )
            logger.info(f"[Scheduler] 자동 포스팅 등록: 매일 {t}")

        self._scheduler.start()
        logger.success("[Scheduler] 자동 스케줄러 시작")

    def _auto_post_wrapper(self, callback: Callable):
        try:
            result = callback()
            if result:
                brand_name, image_paths, caption = result
                self.post_now(brand_name, image_paths, caption)
        except Exception as e:
            logger.error(f"자동 포스팅 콜백 오류: {e}")

    def stop(self):
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("[Scheduler] 스케줄러 중지")

    # ──────────────────────────────────────────────────────────────
    # 이력 조회
    # ──────────────────────────────────────────────────────────────
    def get_history(self, limit: int = 10) -> List[PostJob]:
        return sorted(self._history, key=lambda j: j.posted_at or "")[-limit:]

    def print_history(self, limit: int = 10):
        from rich.table import Table
        from rich.console import Console
        console = Console()
        table = Table(title="📋 포스팅 이력", style="bold")
        table.add_column("브랜드",     style="cyan")
        table.add_column("예약시간",   style="yellow")
        table.add_column("포스팅시간", style="green")
        table.add_column("상태",       style="magenta")
        table.add_column("media_id",  style="white")
        for job in self.get_history(limit):
            table.add_row(
                job.brand_name,
                job.scheduled_at[:16],
                job.posted_at[:16] if job.posted_at else "-",
                "✅ done" if job.status == "done" else
                "❌ failed" if job.status == "failed" else "⏳ pending",
                job.media_id or "-",
            )
        console.print(table)
