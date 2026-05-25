"""
main.py — Instagram 브랜드 카드뉴스 자동화 CLI

사용법:
  python main.py generate --brand "라네즈"
  python main.py post     --brand "라네즈" --now
  python main.py schedule --times "09:00,18:00"
  python main.py history
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List, Optional

import click
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from config import OUTPUT_DIR
from scrapers.brand_info import BrandInfoScraper
from scrapers.financial_data import FinancialDataScraper
from scrapers.olive_young import OliveYoungScraper
from scrapers.naver_smartstore import NaverSmartStoreScraper
from scrapers.amazon import AmazonScraper
from scrapers.tiktok import TikTokScraper
from scrapers.google_trends import GoogleTrendsScraper
from card_news.generator import CardNewsGenerator
from card_news.editorial_generator import EditorialCardNewsGenerator
from instagram.client import InstagramClient
from instagram.scheduler import PostScheduler
from utils.text_utils import build_instagram_caption

console = Console()


# ──────────────────────────────────────────────────────────────────────
# 로거 설정
# ──────────────────────────────────────────────────────────────────────
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
           level="INFO", colorize=True)
logger.add(OUTPUT_DIR / "app.log", rotation="10 MB", level="DEBUG")


# ──────────────────────────────────────────────────────────────────────
# 브랜드 데이터 수집 + 카드뉴스 생성 파이프라인
# ──────────────────────────────────────────────────────────────────────
def run_pipeline(brand_name: str, style: str = "editorial") -> List[Path]:
    """
    전체 파이프라인:
      1. 데이터 수집 (브랜드 정보, 재무, 올리브영, 네이버, 아마존, TikTok, 트렌드)
      2. 카드뉴스 8장 생성
    style: "editorial" (화이트 에디토리얼+Sankey, 기본) | "dark" (레거시 다크+워터폴)
    Returns: 생성된 이미지 경로 리스트
    """
    console.rule(f"[bold magenta]🚀 {brand_name} 브랜드 분석 시작 ({style})[/]")

    steps = [
        ("브랜드 기본 정보 수집",   lambda: BrandInfoScraper().fetch(brand_name)),
        ("재무 데이터 수집",        lambda: FinancialDataScraper().fetch(brand_name)),
        ("올리브영 랭킹 수집",      lambda: OliveYoungScraper().search_brand_rank(brand_name)),
        ("네이버 스마트스토어 수집", lambda: NaverSmartStoreScraper().fetch_brand_products(brand_name)),
        ("아마존 랭킹 수집",        lambda: AmazonScraper().search_brand_rank(brand_name)),
        ("TikTok 트렌드 수집",      lambda: TikTokScraper().fetch_brand_trends(brand_name)),
        ("Google Trends 수집",      lambda: GoogleTrendsScraper().fetch(brand_name)),
    ]

    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("데이터 수집 중...", total=len(steps))
        for desc, fn in steps:
            progress.update(task, description=f"[cyan]{desc}[/]")
            try:
                results.append(fn())
            except Exception as e:
                logger.warning(f"{desc} 실패: {e}")
                results.append(None)
            progress.advance(task)

    brand_info, financial, oy, naver, amazon, tiktok, trends = results

    # fallback
    from scrapers.brand_info import BrandOverview
    from scrapers.financial_data import FinancialSummary
    from scrapers.tiktok import TikTokTrendData
    from scrapers.google_trends import TrendSummary as GTSummary

    brand_info  = brand_info  or BrandOverview(name=brand_name)
    financial   = financial   or FinancialSummary(brand_name=brand_name)
    oy          = oy          or []
    naver       = naver       or []
    amazon      = amazon      or []
    tiktok      = tiktok      or TikTokTrendData(brand_name=brand_name)
    trends      = trends      or GTSummary(brand_name=brand_name)

    # 카드뉴스 생성
    console.rule("[bold cyan]🎨 카드뉴스 생성[/]")
    if style == "dark":
        generator = CardNewsGenerator()
    else:
        generator = EditorialCardNewsGenerator()
    paths = generator.generate(
        brand=brand_info,
        financial=financial,
        oy_products=oy or [],
        naver_products=naver or [],
        amazon_products=amazon or [],
        tiktok=tiktok,
        trends=trends,
    )

    # 결과 출력
    _print_result_table(brand_name, paths)
    return paths


def _print_result_table(brand_name: str, paths: List[Path]):
    table = Table(title=f"✅ {brand_name} 카드뉴스 생성 완료", style="green")
    table.add_column("#", style="dim", width=4)
    table.add_column("파일명",  style="cyan", min_width=25)
    table.add_column("크기",    style="yellow")
    for i, p in enumerate(paths, 1):
        size = f"{p.stat().st_size // 1024} KB" if p.exists() else "N/A"
        table.add_row(str(i), p.name, size)
    console.print(table)


# ──────────────────────────────────────────────────────────────────────
# CLI 명령어
# ──────────────────────────────────────────────────────────────────────
@click.group()
def cli():
    """📸 Instagram 브랜드 카드뉴스 자동화 도구"""
    console.print(Panel.fit(
        "[bold magenta]Instagram Brand CardNews Generator[/]\n"
        "[dim]브랜드 분석 → 카드뉴스 제작 → 자동 포스팅[/]",
        border_style="magenta",
    ))


# ─────────────────────────────────────────
@cli.command()
@click.option("--brand", "-b", required=True, help="분석할 브랜드명 (예: 라네즈)")
@click.option("--output", "-o", default=None, help="출력 디렉토리 (기본: ./output/브랜드명)")
@click.option("--style", "-s",
              type=click.Choice(["editorial", "dark"]), default="editorial",
              help="editorial=화이트+Sankey(기본) / dark=다크+워터폴")
def generate(brand: str, output: Optional[str], style: str):
    """브랜드 분석 + 카드뉴스 이미지 생성"""
    paths = run_pipeline(brand, style=style)
    if output:
        import shutil
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        for p in paths:
            shutil.copy(p, out / p.name)
        console.print(f"[green]📁 복사 완료: {out}[/]")


# ─────────────────────────────────────────
@cli.command()
@click.option("--brand", "-b", required=True, help="브랜드명")
@click.option("--now",   is_flag=True,   help="즉시 포스팅")
@click.option("--time",  "post_time", default=None,
              help="예약 포스팅 시간 (예: 09:00)")
@click.option("--caption-only", is_flag=True, help="캡션만 출력 (업로드 없음)")
@click.option("--style", "-s",
              type=click.Choice(["editorial", "dark"]), default="editorial",
              help="editorial=화이트+Sankey(기본) / dark=다크+워터폴")
def post(brand: str, now: bool, post_time: Optional[str], caption_only: bool,
         style: str):
    """카드뉴스 생성 + Instagram 포스팅"""
    paths = run_pipeline(brand, style=style)
    if not paths:
        console.print("[red]카드뉴스 생성 실패[/]")
        return

    # 캡션 생성
    from scrapers.tiktok import TikTokScraper
    tiktok_data = TikTokScraper().fetch_brand_trends(brand)
    tags = [h.tag.lstrip("#") for h in tiktok_data.hashtags[:10]]
    caption = build_instagram_caption(
        brand_name=brand,
        summary=f"{brand} 브랜드 심층 분석 리포트 📊\n"
                f"재무구조 · 성분분석 · 플랫폼 랭킹 · 투자이력 한눈에!",
        hashtags=tags + ["브랜드분석", "카드뉴스", "뷰티트렌드", "kbeauty",
                         "인스타그램", "뷰티", "스킨케어", "투자"],
    )

    if caption_only:
        console.print(Panel(caption, title="📝 Instagram 캡션", border_style="cyan"))
        return

    ig = InstagramClient()
    scheduler = PostScheduler(ig)

    if now:
        job = scheduler.post_now(brand, paths, caption)
        if job.status == "done":
            console.print(f"[green]✅ 포스팅 완료! media_id={job.media_id}[/]")
        else:
            console.print(f"[red]❌ 포스팅 실패: {job.error}[/]")
    elif post_time:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        scheduled = datetime.fromisoformat(f"{date_str}T{post_time}:00")
        scheduler.enqueue(brand, paths, caption, scheduled)
        scheduler.process_queue()
        console.print(f"[cyan]⏰ 예약 포스팅 등록: {post_time}[/]")
    else:
        console.print("[yellow]--now 또는 --time HH:MM 옵션을 지정하세요.[/]")


# ─────────────────────────────────────────
@cli.command()
@click.option("--times", "-t", default=None,
              help="포스팅 시간 (예: '09:00,18:00')")
@click.option("--brands", "-b", default=None,
              help="자동 분석 브랜드 목록 (쉼표 구분, 예: '라네즈,이니스프리')")
def schedule(times: Optional[str], brands: Optional[str]):
    """자동 스케줄 포스팅 설정 및 시작"""
    brand_list = [b.strip() for b in brands.split(",")] if brands else []
    time_list  = [t.strip() for t in times.split(",")]  if times  else None

    ig = InstagramClient()
    scheduler = PostScheduler(ig)

    brand_idx = [0]  # 순환 인덱스

    def auto_callback():
        if not brand_list:
            return None
        b = brand_list[brand_idx[0] % len(brand_list)]
        brand_idx[0] += 1
        paths = run_pipeline(b)
        if not paths:
            return None
        tags = ["브랜드분석", "카드뉴스", "kbeauty"]
        caption = build_instagram_caption(b, f"{b} 분석 리포트", tags)
        return b, paths, caption

    scheduler.start_auto_schedule(auto_callback, time_list)
    console.print(f"[green]🤖 자동 스케줄러 시작! 시간: {time_list or '설정 기본값'}[/]")
    console.print("[dim]Ctrl+C 로 종료[/]")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()
        console.print("[yellow]스케줄러 중지[/]")


# ─────────────────────────────────────────
@cli.command()
@click.option("--limit", "-n", default=20, help="출력 건수")
def history(limit: int):
    """포스팅 이력 조회"""
    scheduler = PostScheduler()
    scheduler.print_history(limit)


# ─────────────────────────────────────────
@cli.command()
def account():
    """Instagram 계정 정보 조회"""
    ig = InstagramClient()
    if ig.login():
        info = ig.get_account_info()
        if info:
            table = Table(title="📱 Instagram 계정 정보", style="cyan")
            table.add_column("항목", style="dim")
            table.add_column("값",   style="white")
            for k, v in info.items():
                table.add_row(k, str(v))
            console.print(table)
        ig.logout()


# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cli()
