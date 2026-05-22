from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .utils import clamp_score, clean_numeric, ramp_down_penalty, ramp_up_penalty, save_line_plot, safe_ratio


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

    penalty_parts = {
        "diff_penalty": ramp_down_penalty(normalized_diff, 0.025, 0.0, 28),
        "diff_cv_penalty": ramp_down_penalty(diff_cv, 0.35, 0.0, 24),
        "second_diff_penalty": ramp_down_penalty(second_diff_std_ratio, 0.001, 0.0, 24) if value_range > 0 else 0.0,
        "rolling_variance_penalty": ramp_up_penalty(low_rolling_var_rate, 0.45, 1.0, 16),
        "pct_change_penalty": ramp_down_penalty(pct_std, 0.01, 0.0, 12) if value_range > 0 else 0.0,
    }
    penalty = sum(penalty_parts.values())
    reasons: list[str] = []
    if penalty_parts["diff_penalty"] > 0:
        reasons.append("一阶差分相对整体波动范围过小，序列可能过于平滑。")
    if penalty_parts["diff_cv_penalty"] > 0:
        reasons.append("相邻变化幅度高度稳定，缺少真实采集数据常见的随机扰动。")
    if penalty_parts["second_diff_penalty"] > 0:
        reasons.append("二阶差分几乎没有波动，序列可能接近人工线性生成。")
    if penalty_parts["rolling_variance_penalty"] > 0:
        reasons.append("较多窗口内 rolling variance 偏低，局部波动不足。")
    if penalty_parts["pct_change_penalty"] > 0:
        reasons.append("变化率标准差偏低，增长或下降节奏过于整齐。")

    if not reasons:
        reasons.append("序列存在一定自然波动，未发现明显过度平滑特征。")

    chart = save_line_plot(values, f"平滑度走势 - {series.name}", reports_dir, f"smoothness_{series.name}")
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
            **{key: round(value, 4) for key, value in penalty_parts.items()},
        },
        "charts": [chart] if chart else [],
    }
