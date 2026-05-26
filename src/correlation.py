from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path.cwd() / ".cache"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd

from .utils import clamp_score, configure_chinese_font, ramp_up_penalty


configure_chinese_font()


def analyze_correlations(df: pd.DataFrame, numeric_columns: list[str], reports_dir: Path) -> dict:
    if len(numeric_columns) < 2:
        return {"score": 70.0, "risk": "limited", "reasons": ["数值列少于 2 个，无法充分进行多变量相关性检测。"], "metrics": {}, "charts": []}

    numeric_df = df[numeric_columns].apply(pd.to_numeric, errors="coerce").dropna(how="all")
    pearson = numeric_df.corr(method="pearson")
    spearman = numeric_df.corr(method="spearman")
    pairs: list[tuple[str, str, float, float]] = []
    for i, left in enumerate(numeric_columns):
        for right in numeric_columns[i + 1:]:
            p = pearson.loc[left, right]
            s = spearman.loc[left, right]
            if pd.notna(p) and pd.notna(s):
                pairs.append((left, right, float(p), float(s)))

    high_pairs = [(a, b, p, s) for a, b, p, s in pairs if max(abs(p), abs(s)) > 0.99]
    very_high_pairs = [(a, b, p, s) for a, b, p, s in pairs if max(abs(p), abs(s)) > 0.999]
    average_abs_corr = float(np.mean([abs(p) for _, _, p, _ in pairs])) if pairs else 0.0
    max_abs_corr = float(max((max(abs(p), abs(s)) for _, _, p, s in pairs), default=0.0))

    penalty_parts = {
        "perfect_correlation_penalty": ramp_up_penalty(max_abs_corr, 0.999, 1.0, 35),
        "high_correlation_penalty": ramp_up_penalty(min(max_abs_corr, 0.999), 0.99, 0.999, 14),
        "average_correlation_penalty": ramp_up_penalty(average_abs_corr, 0.96, 1.0, 18) if len(pairs) >= 3 else 0.0,
    }
    penalty = sum(penalty_parts.values())
    reasons: list[str] = []
    if very_high_pairs:
        examples = "; ".join(f"{a}-{b}: Pearson={p:.3f}, Spearman={s:.3f}" for a, b, p, s in very_high_pairs[:3])
        reasons.append(f"存在近乎完美相关的变量对，可能是线性推导或复制生成：{examples}")
    elif high_pairs:
        examples = "; ".join(f"{a}-{b}: Pearson={p:.3f}, Spearman={s:.3f}" for a, b, p, s in high_pairs[:3])
        reasons.append(f"存在过强相关的变量对，需要业务解释：{examples}")
    if penalty_parts["average_correlation_penalty"] > 0:
        reasons.append("整体平均相关性偏高，多变量之间可能过于同步。")
    if not reasons:
        reasons.append("变量之间未发现明显完美线性关系或整体过强同步。")

    charts: list[str] = []
    reports_dir.mkdir(parents=True, exist_ok=True)
    chart_path = reports_dir / f"correlation_heatmap_{uuid4().hex[:8]}.png"
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(pearson.fillna(0), vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(range(len(numeric_columns)), numeric_columns, rotation=45, ha="right")
    ax.set_yticks(range(len(numeric_columns)), numeric_columns)
    ax.set_title("Pearson 相关性热力图")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(chart_path, dpi=150)
    plt.close(fig)
    charts.append(str(chart_path))

    return {
        "score": clamp_score(100 - penalty),
        "risk": "ok" if penalty < 30 else "attention",
        "reasons": reasons,
        "metrics": {
            "pair_count": len(pairs),
            "high_correlation_pairs": len(high_pairs),
            "very_high_correlation_pairs": len(very_high_pairs),
            "average_abs_pearson": round(average_abs_corr, 4),
            "max_abs_correlation": round(max_abs_corr, 4),
            **{key: round(value, 4) for key, value in penalty_parts.items()},
        },
        "charts": charts,
        "pearson": pearson,
        "spearman": spearman,
    }
