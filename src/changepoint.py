from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .utils import clamp_score, clean_numeric, ramp_up_penalty, safe_filename_part, safe_ratio


def _page_hinkley(values: np.ndarray, delta: float) -> tuple[float, int | None]:
    mean = 0.0
    cumulative = 0.0
    min_cumulative = 0.0
    max_stat = 0.0
    max_index: int | None = None
    for idx, value in enumerate(values, start=1):
        mean += (value - mean) / idx
        cumulative += value - mean - delta
        if cumulative < min_cumulative:
            min_cumulative = cumulative
        stat = cumulative - min_cumulative
        if stat > max_stat:
            max_stat = float(stat)
            max_index = idx - 1
    return max_stat, max_index


def _save_changepoint_plot(values: pd.Series, reports_dir: Path, prefix: str, point: int | None) -> str | None:
    if len(values) < 2:
        return None
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{safe_filename_part(prefix)}_{uuid4().hex[:8]}.png"
    fig, ax = plt.subplots(figsize=(8, 3.2))
    x = np.arange(len(values))
    ax.plot(x, values.to_numpy(), linewidth=1.6)
    if point is not None and 0 <= point < len(values):
        ax.axvline(point, color="#c2413a", linestyle="--", linewidth=1.4, label="疑似变化点")
        ax.legend(loc="best")
    ax.set_title(f"变化点扫描 - {values.name}")
    ax.set_xlabel("样本序号")
    ax.set_ylabel(values.name or "数值")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return str(path)


def analyze_changepoints(series: pd.Series, reports_dir: Path) -> dict:
    values = clean_numeric(series).reset_index(drop=True)
    if len(values) < 20:
        return {
            "score": 65.0,
            "risk": "limited",
            "reasons": ["样本量偏少，变化点检测只能作为弱提示。"],
            "metrics": {},
            "charts": [],
        }

    arr = values.to_numpy()
    n = len(arr)
    std = float(np.std(arr)) or 1e-9
    scale = max(float(np.max(arr) - np.min(arr)), std, 1e-9)

    window = min(max(5, n // 6), 20)
    best_window_ratio = 0.0
    best_window_index: int | None = None
    for idx in range(window, n - window + 1):
        left = arr[idx - window : idx]
        right = arr[idx : idx + window]
        ratio = safe_ratio(abs(float(np.mean(right) - np.mean(left))), scale)
        if ratio > best_window_ratio:
            best_window_ratio = ratio
            best_window_index = idx

    centered = arr - float(np.mean(arr))
    cusum = np.cumsum(centered)
    cusum_ratio = safe_ratio(float(np.max(cusum) - np.min(cusum)), std * n)
    cusum_index = int(np.argmax(np.abs(cusum - np.mean(cusum)))) if len(cusum) else None

    ph_stat, ph_index = _page_hinkley(arr, delta=0.005 * std)
    ph_ratio = safe_ratio(ph_stat, std * np.sqrt(n))
    point_candidates = [item for item in [best_window_index, cusum_index, ph_index] if item is not None]
    likely_point = int(np.median(point_candidates)) if point_candidates else None

    penalty_parts = {
        "sliding_mean_penalty": ramp_up_penalty(best_window_ratio, 0.25, 0.80, 35),
        "cusum_penalty": ramp_up_penalty(cusum_ratio, 0.18, 0.45, 25),
        "page_hinkley_penalty": ramp_up_penalty(ph_ratio, 2.5, 5.0, 25),
    }
    penalty = sum(penalty_parts.values())

    reasons: list[str] = []
    if penalty_parts["sliding_mean_penalty"] > 0:
        reasons.append("滑动窗口前后均值差异较大，可能存在阶段性突变或校准前后差异。")
    if penalty_parts["cusum_penalty"] > 0:
        reasons.append("CUSUM 曲线出现明显累积偏移，提示序列可能存在结构性变化。")
    if penalty_parts["page_hinkley_penalty"] > 0:
        reasons.append("Page-Hinkley 统计量偏高，需复核是否有突发设备状态变化或数据处理分段。")
    if not reasons:
        reasons.append("未发现明显变化点信号；序列阶段性结构较稳定。")

    chart = _save_changepoint_plot(values, reports_dir, f"changepoint_{series.name}", likely_point)
    return {
        "score": clamp_score(100 - penalty),
        "risk": "ok" if penalty < 30 else "attention",
        "reasons": reasons,
        "metrics": {
            "window_size": window,
            "best_window_index": best_window_index,
            "best_window_mean_shift_ratio": round(best_window_ratio, 4),
            "cusum_ratio": round(cusum_ratio, 4),
            "cusum_index": cusum_index,
            "page_hinkley_ratio": round(ph_ratio, 4),
            "page_hinkley_index": ph_index,
            "likely_changepoint_index": likely_point,
            **{key: round(value, 4) for key, value in penalty_parts.items()},
        },
        "charts": [chart] if chart else [],
    }
