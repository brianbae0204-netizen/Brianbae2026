"""
waterfall_chart.py — P&L 워터폴 차트 생성 (matplotlib)
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager
import numpy as np

from config import CardConfig, FONTS_DIR
from utils.image_utils import load_korean_font_path


class WaterfallChart:
    """Instagram 카드뉴스용 워터폴 차트"""

    def __init__(self):
        self._setup_fonts()

    def _setup_fonts(self):
        """한글 폰트 등록"""
        font_path = load_korean_font_path()
        if font_path:
            font_manager.fontManager.addfont(str(font_path))
            prop = font_manager.FontProperties(fname=str(font_path))
            plt.rcParams["font.family"] = prop.get_name()
        plt.rcParams.update({
            "axes.unicode_minus": False,
            "figure.facecolor":   "#0F0F1A",
            "axes.facecolor":     "#0F0F1A",
            "axes.edgecolor":     "#2A2A3E",
            "text.color":         "#FFFFFF",
            "axes.labelcolor":    "#FFFFFF",
            "xtick.color":        "#B0BEC5",
            "ytick.color":        "#B0BEC5",
            "grid.color":         "#1E1E30",
            "grid.alpha":         0.6,
        })

    def create(
        self,
        data: List[Dict],
        title: str = "손익 구조",
        subtitle: str = "",
        figsize: Tuple[int, int] = (11, 7),
        save_path: Optional[Path] = None,
    ) -> plt.Figure:
        """
        워터폴 차트 생성

        data 형식:
        [
          {"label": "매출액",    "value": 1850.0, "type": "total"},
          {"label": "매출원가",  "value": -740.0, "type": "negative"},
          {"label": "매출총이익","value": 1110.0, "type": "subtotal"},
          ...
        ]
        """
        fig, ax = plt.subplots(figsize=figsize, dpi=150)
        fig.patch.set_facecolor("#0F0F1A")
        ax.set_facecolor("#0F0F1A")

        n = len(data)
        labels  = [d["label"] for d in data]
        values  = [d["value"] for d in data]
        types   = [d["type"]  for d in data]

        # ── 누적 bottom 계산 ─────────────────────────────────────
        running = 0.0
        bottoms = []
        bar_vals = []

        for i, (v, t) in enumerate(zip(values, types)):
            if t in ("total", "subtotal"):
                bottoms.append(0)
                bar_vals.append(abs(v))
                running = v
            else:
                if v >= 0:
                    bottoms.append(running)
                    bar_vals.append(v)
                    running += v
                else:
                    bottoms.append(running + v)
                    bar_vals.append(abs(v))
                    running += v

        # ── 색상 지정 ────────────────────────────────────────────
        colors = []
        for t, v in zip(types, values):
            if t == "total":
                colors.append(CardConfig.TOTAL_COLOR)
            elif t == "subtotal":
                colors.append("#7C4DFF")
            elif v >= 0:
                colors.append(CardConfig.POSITIVE_COLOR)
            else:
                colors.append(CardConfig.NEGATIVE_COLOR)

        x = np.arange(n)
        bar_width = 0.6

        # ── 막대 그리기 ──────────────────────────────────────────
        bars = ax.bar(x, bar_vals, bottom=bottoms, color=colors,
                      width=bar_width, zorder=3, edgecolor="#0F0F1A",
                      linewidth=0.5, alpha=0.92)

        # ── 연결선 ───────────────────────────────────────────────
        for i in range(n - 1):
            t = types[i]
            if t not in ("total", "subtotal"):
                end_y = bottoms[i] + bar_vals[i] if values[i] >= 0 else bottoms[i]
            else:
                end_y = bar_vals[i]
            ax.plot(
                [x[i] + bar_width / 2, x[i + 1] - bar_width / 2],
                [end_y, end_y],
                color="#555577", linewidth=1.0, linestyle="--", zorder=2
            )

        # ── 값 레이블 ────────────────────────────────────────────
        for i, (bar, bv, bt, t) in enumerate(zip(bars, bar_vals, bottoms, types)):
            center_y = bt + bv / 2
            val_str = f"{'+' if values[i] > 0 and t not in ('total','subtotal') else ''}" \
                      f"{values[i]:,.0f}억"
            ax.text(
                x[i], center_y, val_str,
                ha="center", va="center",
                fontsize=8.5, fontweight="bold",
                color="white", zorder=5
            )
            # 상단 레이블 (percent if possible)
            top_y = bt + bv + (max(bar_vals) * 0.01)
            if t in ("subtotal", "total") and values[i] != 0:
                ax.text(x[i], top_y, f"{abs(values[i]):,.0f}억",
                        ha="center", va="bottom", fontsize=7, color="#B0BEC5")

        # ── x축 라벨 ────────────────────────────────────────────
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9, rotation=15, ha="right")

        # ── y축 포맷 ────────────────────────────────────────────
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}억")
        )
        ax.set_ylabel("금액 (억 원)", fontsize=9, color="#B0BEC5", labelpad=8)

        # ── 그리드 ──────────────────────────────────────────────
        ax.yaxis.grid(True, zorder=0, alpha=0.3, color="#2A2A4A")
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#2A2A4A")
        ax.spines["bottom"].set_color("#2A2A4A")

        # ── 제목 ────────────────────────────────────────────────
        fig.text(0.5, 0.97, title,
                 ha="center", va="top", fontsize=14, fontweight="bold",
                 color="#FFFFFF")
        if subtitle:
            fig.text(0.5, 0.93, subtitle,
                     ha="center", va="top", fontsize=10, color="#B0BEC5")

        # ── 범례 ────────────────────────────────────────────────
        legend_items = [
            mpatches.Patch(color=CardConfig.TOTAL_COLOR,    label="합계/매출"),
            mpatches.Patch(color="#7C4DFF",                  label="중간 소계"),
            mpatches.Patch(color=CardConfig.POSITIVE_COLOR, label="이익 항목"),
            mpatches.Patch(color=CardConfig.NEGATIVE_COLOR, label="비용 항목"),
        ]
        ax.legend(handles=legend_items, loc="upper right",
                  fontsize=7.5, framealpha=0.3, facecolor="#1A1A2E",
                  edgecolor="#2A2A4A", labelcolor="white")

        plt.tight_layout(rect=[0, 0, 1, 0.92])

        if save_path:
            fig.savefig(str(save_path), dpi=150, bbox_inches="tight",
                        facecolor="#0F0F1A", edgecolor="none")
            logger.info(f"워터폴 차트 저장: {save_path}")  # type: ignore[name-defined]

        return fig

    def create_yoy_comparison(
        self,
        pl_list: List,   # List[PLStatement]
        save_path: Optional[Path] = None,
    ) -> plt.Figure:
        """연도별 P&L 비교 차트"""
        if not pl_list:
            raise ValueError("P&L 데이터 없음")

        fig, axes = plt.subplots(1, len(pl_list), figsize=(14, 7), dpi=150)
        if len(pl_list) == 1:
            axes = [axes]
        fig.patch.set_facecolor("#0F0F1A")

        for ax, pl in zip(axes, pl_list):
            data = pl.to_waterfall()
            if not data:
                continue
            # 각 연도별 미니 워터폴
            self._draw_mini_waterfall(ax, data, f"{pl.year}년")

        fig.suptitle("연도별 손익 구조 비교", fontsize=14, color="white",
                     fontweight="bold", y=1.02)
        plt.tight_layout()

        if save_path:
            fig.savefig(str(save_path), dpi=150, bbox_inches="tight",
                        facecolor="#0F0F1A")
        return fig

    def _draw_mini_waterfall(self, ax, data: List[Dict], year_label: str):
        """서브플롯용 미니 워터폴"""
        ax.set_facecolor("#0F0F1A")
        ax.set_title(year_label, color="white", fontsize=11, fontweight="bold")
        n = len(data)
        x = np.arange(n)
        running = 0.0
        for i, d in enumerate(data):
            v, t = d["value"], d["type"]
            if t in ("total", "subtotal"):
                bottom, height = 0, abs(v)
                running = v
            elif v >= 0:
                bottom, height = running, v
                running += v
            else:
                bottom, height = running + v, abs(v)
                running += v

            color = (CardConfig.TOTAL_COLOR if t == "total"
                     else "#7C4DFF" if t == "subtotal"
                     else CardConfig.POSITIVE_COLOR if v >= 0
                     else CardConfig.NEGATIVE_COLOR)
            ax.bar(i, height, bottom=bottom, color=color,
                   width=0.6, alpha=0.9, edgecolor="#0F0F1A", linewidth=0.5)
            ax.text(i, bottom + height / 2, f"{v:,.0f}",
                    ha="center", va="center", fontsize=6.5,
                    color="white", fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels([d["label"] for d in data],
                           fontsize=6.5, rotation=30, ha="right", color="#B0BEC5")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#2A2A4A")
        ax.spines["bottom"].set_color("#2A2A4A")
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}")
        )
        ax.tick_params(colors="#B0BEC5")


# 로거 import 추가 (파일 하단)
from loguru import logger
import matplotlib.ticker
