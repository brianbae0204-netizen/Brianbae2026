"""
sankey_chart.py — 손익 Sankey(자금 흐름) 차트
  • ekke.now '싸이는 이렇게 벌고 쓴다' 스타일
  • 매출(파랑) → 매출원가/판관비/이익 으로 갈라지는 리본 흐름
  • 판관비는 세부 항목(인건비/광고선전비/운영관리비/감가상각비/기타)으로 fan-out
  • matplotlib 베지어 리본으로 직접 렌더 (kaleido/크로뮴 의존성 없음)
  • 흑자/적자(순손실) 모두 지원
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path as MplPath
from matplotlib import font_manager
import numpy as np
from loguru import logger

from config import EditorialTheme as ET
from utils.image_utils import load_korean_font_path


# ──────────────────────────────────────────────────────────────────────
@dataclass
class _Node:
    name:   str
    value:  float
    color:  str
    x:      float          # 0~1
    y0:     float          # 하단 (값 기준)
    y1:     float          # 상단
    label_side: str = "right"   # left | right | top


class SankeyPLChart:
    """손익 Sankey 흐름도 생성기"""

    def __init__(self):
        self._setup_fonts()

    def _setup_fonts(self):
        fp = load_korean_font_path()
        if fp:
            font_manager.fontManager.addfont(str(fp))
            prop = font_manager.FontProperties(fname=str(fp))
            self.font_name = prop.get_name()
            plt.rcParams["font.family"] = self.font_name
        else:
            self.font_name = "sans-serif"
        plt.rcParams["axes.unicode_minus"] = False

    # ──────────────────────────────────────────────────────────────
    # 베지어 리본
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _ribbon(ax, x0, y0_top, y0_bot, x1, y1_top, y1_bot,
                color, alpha=0.55):
        cx = (x0 + x1) / 2.0
        verts = [
            (x0, y0_top),
            (cx, y0_top), (cx, y1_top), (x1, y1_top),
            (x1, y1_bot),
            (cx, y1_bot), (cx, y0_bot), (x0, y0_bot),
            (x0, y0_top),
        ]
        codes = [
            MplPath.MOVETO,
            MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
            MplPath.LINETO,
            MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
            MplPath.CLOSEPOLY,
        ]
        patch = mpatches.PathPatch(MplPath(verts, codes),
                                   facecolor=color, edgecolor="none",
                                   alpha=alpha, zorder=1)
        ax.add_patch(patch)

    @staticmethod
    def _node_bar(ax, x, y0, y1, color, width=0.018):
        ax.add_patch(mpatches.Rectangle(
            (x - width / 2, y0), width, y1 - y0,
            facecolor=color, edgecolor="none", zorder=3))

    @staticmethod
    def _fmt(v: float) -> str:
        """억 원 → 보기 좋은 한국어 표기"""
        if abs(v) >= 1:
            return f"{v:,.0f}억 원"
        else:
            man = v * 10000  # 억 → 만
            return f"{man:,.0f}만 원"

    # ──────────────────────────────────────────────────────────────
    # 판관비 세부 항목 추정 (PLStatement엔 세부가 없으므로 화장품 업계 평균 비율)
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _breakdown_opex(opex: float) -> List[Tuple[str, float]]:
        ratios = [
            ("인건비",     0.42),
            ("광고선전비", 0.30),
            ("운영관리비", 0.14),
            ("감가상각비", 0.08),
            ("기타비용",   0.06),
        ]
        return [(name, round(opex * r, 1)) for name, r in ratios]

    # ──────────────────────────────────────────────────────────────
    # 메인 생성
    # ──────────────────────────────────────────────────────────────
    def create(
        self,
        pl,                       # PLStatement
        brand_name: str,
        figsize: Tuple[float, float] = (10.8, 9.6),
        save_path: Optional[Path] = None,
    ) -> Image.Image:  # type: ignore[name-defined]
        revenue = pl.revenue or 0
        cogs    = pl.cogs or 0
        opex    = pl.selling_expenses or 0
        op_inc  = pl.operating_income
        tax     = pl.tax or 0
        net     = pl.net_income or 0
        non_op  = 0  # 영업외이익(추정 생략)

        if op_inc is None:
            op_inc = revenue - cogs - opex

        is_loss = net < 0

        fig, ax = plt.subplots(figsize=figsize, dpi=150)
        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#FFFFFF")
        ax.set_xlim(0, 1.16)          # 우측 라벨 여백 확보
        ax.set_ylim(0, 1)
        ax.axis("off")

        # 그리기 영역(세로)
        TOP, BOT = 0.92, 0.08
        DH = TOP - BOT
        total = max(revenue, cogs + opex + max(op_inc, 0)) or 1
        scale = DH / total

        # 컬럼 x 좌표 (좌:매출 / 중:원가·판관비·이익 / 우:세부)
        X0, X1, X2 = 0.14, 0.46, 0.78

        # ── 좌측: 총 매출 노드 (전체 높이) ──────────────────────
        rev_y1, rev_y0 = TOP, TOP - revenue * scale
        self._node_bar(ax, X0, rev_y0, rev_y1, ET.SANKEY_REVENUE)
        ax.text(X0 - 0.03, (rev_y0 + rev_y1) / 2 + 0.018, "총 매출",
                ha="right", va="center", fontsize=16, fontweight="bold",
                color="#1E3A8A")
        ax.text(X0 - 0.03, (rev_y0 + rev_y1) / 2 - 0.022, self._fmt(revenue),
                ha="right", va="center", fontsize=14, color="#1E3A8A")

        # ── 중앙 컬럼: 매출원가 / 판관비 / 영업이익 (위→아래 스택) ──
        mid_items = [
            ("매출원가", cogs,   ET.SANKEY_COST),
            ("판관비",   opex,   ET.SANKEY_COST),
            ("영업이익", max(op_inc, 0),
             ET.SANKEY_PROFIT if op_inc >= 0 else ET.SANKEY_COST),
        ]
        gap = 0.014
        mid_nodes: Dict[str, _Node] = {}
        cur = TOP
        for name, val, color in mid_items:
            hh = val * scale
            mid_nodes[name] = _Node(name, val, color, X1, cur - hh, cur)
            cur -= hh + gap

        # 매출 리본 (총매출 → 각 중앙노드)
        src_top = TOP
        for name, val, color in mid_items:
            n = mid_nodes[name]
            rc = ET.SANKEY_PRO_LT if name == "영업이익" else ET.SANKEY_REV_LT
            self._ribbon(ax, X0 + 0.009, src_top, src_top - val * scale,
                         X1 - 0.007, n.y1, n.y0, rc, alpha=0.6)
            src_top -= val * scale
            self._node_bar(ax, X1, n.y0, n.y1, color)

        # 매출원가 라벨 (큰 빨강, 세부 분해 없음 → 우측 비움)
        cogs_n = mid_nodes["매출원가"]
        ax.text(X1 + 0.024, (cogs_n.y0 + cogs_n.y1) / 2 + 0.016, "매출원가",
                ha="left", va="center", fontsize=16, fontweight="bold",
                color="#B91C1C")
        ax.text(X1 + 0.024, (cogs_n.y0 + cogs_n.y1) / 2 - 0.02, self._fmt(cogs),
                ha="left", va="center", fontsize=14, color="#B91C1C")

        # ── 우측 컬럼: 판관비 세부 + 세금/순이익 (단일 세로 스택) ───
        opex_n  = mid_nodes["판관비"]
        opinc_n = mid_nodes["영업이익"]

        # (이름, 값, 노드색, 소스노드, 이익여부)
        right_items = []
        for nm, vv in self._breakdown_opex(opex):
            right_items.append((nm, vv, ET.SANKEY_COST, opex_n, False))
        if op_inc >= 0:
            if tax:
                right_items.append(("법인세", tax, ET.SANKEY_COST, opinc_n, False))
            if net:
                right_items.append(("순이익", abs(net), ET.SANKEY_PROFIT,
                                    opinc_n, True))

        self._place_right_stack(ax, right_items, X_src=X1, X_dst=X2,
                                scale=scale, top=TOP, bot=BOT)

        # 중앙 노드 라벨 (안쪽)
        ax.text(X1 - 0.016, (opex_n.y0 + opex_n.y1) / 2, "판관비",
                ha="right", va="center", fontsize=11, color="#B91C1C")
        if op_inc >= 0:
            ax.text(X1 - 0.016, (opinc_n.y0 + opinc_n.y1) / 2, "영업이익",
                    ha="right", va="center", fontsize=11, color="#15803D")

        # ── 적자(순손실) 표기 ──────────────────────────────────
        if is_loss:
            ax.text(X1, BOT - 0.05, f"순손실  {self._fmt(abs(net))}",
                    ha="center", va="center", fontsize=16, fontweight="bold",
                    color="#B91C1C")

        # ── 범례 (좌상단, 내부 제목은 카드가 담당하므로 생략) ──────
        legend = [
            mpatches.Patch(color=ET.SANKEY_REVENUE, label="매출"),
            mpatches.Patch(color=ET.SANKEY_PROFIT,  label="이익"),
            mpatches.Patch(color=ET.SANKEY_COST,    label="비용"),
        ]
        ax.legend(handles=legend, loc="upper left",
                  bbox_to_anchor=(0.0, 1.0), fontsize=13,
                  frameon=False, labelcolor="#333333", ncol=3,
                  columnspacing=1.2, handlelength=1.0)

        plt.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)

        # PIL 변환
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, facecolor="#FFFFFF",
                    bbox_inches="tight", pad_inches=0.1)
        plt.close(fig)
        buf.seek(0)
        from PIL import Image
        img = Image.open(buf).convert("RGB").copy()
        if save_path:
            img.save(str(save_path))
            logger.info(f"Sankey 차트 저장: {save_path}")
        return img

    # ──────────────────────────────────────────────────────────────
    def _place_right_stack(self, ax, items, X_src, X_dst, scale, top, bot):
        """우측 세부 항목 전체를 하나의 세로 스택으로 배치.
        items: (이름, 값, 노드색, 소스노드, 이익여부)
        각 항목은 자신의 소스노드(판관비/영업이익)에서 리본을 받는다.
        라벨(2줄) 겹침 방지를 위해 목적지는 최소 간격 균등 배치."""
        n = len(items)
        if n == 0:
            return
        MIN_SLOT = 0.058
        slot_gap = 0.008
        slots = [max(v * scale, MIN_SLOT) for _, v, _, _, _ in items]
        total = sum(slots) + slot_gap * (n - 1)

        # 전체 스택을 그리기 영역 세로 중앙에 배치 (위로 넘치지 않게 clamp)
        dst_top = (top + bot) / 2 + total / 2
        dst_top = min(top, dst_top)

        # 소스 노드별 소비 커서 (위→아래)
        src_cursor: Dict[int, float] = {}
        dst_cur = dst_top
        for (name, val, color, src_node, is_profit), slot_h in zip(items, slots):
            hh = val * scale
            sid = id(src_node)
            s_top = src_cursor.get(sid, src_node.y1)
            dy1, dy0 = dst_cur, dst_cur - slot_h
            ribbon_c = ET.SANKEY_PRO_LT if is_profit else ET.SANKEY_COST_LT
            self._ribbon(ax, X_src + 0.009, s_top, s_top - hh,
                         X_dst - 0.007, dy1, dy0, ribbon_c, alpha=0.55)
            self._node_bar(ax, X_dst, dy0, dy1, color, width=0.013)
            lc = "#15803D" if is_profit else "#B91C1C"
            cy = (dy0 + dy1) / 2
            ax.text(X_dst + 0.022, cy + 0.013, name,
                    ha="left", va="center", fontsize=12.5, fontweight="bold",
                    color=lc)
            ax.text(X_dst + 0.022, cy - 0.017, self._fmt(val),
                    ha="left", va="center", fontsize=11, color=lc)
            src_cursor[sid] = s_top - hh
            dst_cur = dy0 - slot_gap


# PIL import (타입 힌트용)
from PIL import Image  # noqa: E402
