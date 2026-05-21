from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .utils import clamp_score, clean_numeric, save_line_plot, safe_ratio


def analyze_smoothness(series: pd.Series, reports_dir: Path) -> dict:
    values = clean_numeric(series)
    if len(values) < 8:
        return {"score": 50.0, "risk": "insufficient_data", "reasons": ["样本过少，平滑度判断不稳定。"], "metrics": {}, "charts": []}

    diffs = values.diff().dropna()
    pct_change = values.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    rolling_var = values.rolling(window=min(7, max(3, len(values) // 8))).var().dropna()
    second_diffs = diffs.diff().dropna()

    mean_abs_diff = float(diffs.abs().mean())
    value_range = float(values.max() - values.min())
    normalized_diff = safe_ratio(mean_abs_diff, value_range)
    diff_cv = safe_ratio(float(diffs.std()), float(abs(diffs.mean())) + 1e-9)
    second_diff_std_ratio = safe_ratio(float(second_diffs.std()), value_range)
    low_rolling_var_rate = float((rolling_var < rolling_var.quantile(0.2)).mean()) if len(rolling_var) else 0.0
    pct_std = float(pct_change.std()) if len(pct_change) else 0.0

    penalty = 0.0
    reasons: list[str] = []
    if normalized_diff < 0.025:
        penalty += 28
        reasons.append("一阶差分相对整体波动范围过小，序列可能过于平滑。")
    if diff_cv < 0.35:
        penalty += 24
        reasons.append("相邻变化幅度高度稳定，缺少真实采集数据常见的随机扰动。")
    if second_diff_std_ratio < 0.001 and value_range > 0:
        penalty += 24
        reasons.append("二阶差分几乎没有波动，序列可能接近人工线性生成。")
    if low_rolling_var_rate > 0.45:
        penalty += 16
        reasons.append("较多窗口内 rolling variance 偏低，局部波动不足。")
    if pct_std < 0.01 and value_range > 0:
        penalty += 12
        reasons.append("变化率标准差偏低，增长或下降节奏过于整齐。")

    if not reasons:
        reasons.append("序列存在一定自然波动，未发现明显过度平滑特征。")

    chart = save_line_plot(values, f"Smoothness - {series.name}", reports_dir, f"smoothness_{series.name}")
    return {
        "score": clamp_score(100 - penalty),
        "risk": "ok" if penalty < 30 else "attention",
        "reasons": reasons,
        "metrics": {
            "normalized_mean_abs_diff": round(normalized_diff, 4),
            "diff_cv": round(diff_cv, 4),
            "second_diff_std_ratio": round(second_diff_std_ratio, 4),
            "low_rolling_variance_rate": round(low_rolling_var_rate, 4),
            "pct_change_std": round(pct_std, 4),
        },
        "charts": [chart] if chart else [],
    }
