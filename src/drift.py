from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .utils import clamp_score, clean_numeric, ramp_up_penalty, safe_ratio, save_line_plot


def analyze_sensor_drift(series: pd.Series, reports_dir: Path) -> dict:
    values = clean_numeric(series).reset_index(drop=True)
    if len(values) < 20:
        return {
            "score": 65.0,
            "risk": "limited",
            "reasons": ["样本量偏少，传感器漂移检测只能作为弱提示。"],
            "metrics": {},
            "charts": [],
        }

    n = len(values)
    value_range = float(values.max() - values.min())
    std = float(values.std(ddof=0)) or 1e-9
    scale = max(value_range, std, 1e-9)
    window = min(max(5, n // 5), max(5, n // 3))

    head = values.iloc[:window]
    tail = values.iloc[-window:]
    head_mean = float(head.mean())
    tail_mean = float(tail.mean())
    head_std = float(head.std(ddof=0)) or 0.0
    tail_std = float(tail.std(ddof=0)) or 0.0

    mean_shift_ratio = safe_ratio(abs(tail_mean - head_mean), scale)
    variance_shift_ratio = safe_ratio(abs(tail_std - head_std), std)

    rolling_window = min(max(5, n // 8), 20)
    rolling_mean = values.rolling(window=rolling_window, min_periods=rolling_window).mean().dropna()
    if len(rolling_mean) >= 3:
        x = np.arange(len(rolling_mean))
        slope = float(np.polyfit(x, rolling_mean.to_numpy(), 1)[0])
        rolling_slope_ratio = safe_ratio(abs(slope) * max(len(rolling_mean) - 1, 1), scale)
    else:
        rolling_slope_ratio = 0.0

    centered = values - values.mean()
    cusum = centered.cumsum()
    cusum_range = safe_ratio(float(cusum.max() - cusum.min()), std * n)

    diffs = values.diff().dropna()
    signs = np.sign(diffs.to_numpy())
    signs = signs[signs != 0]
    sign_imbalance = abs(float(signs.mean())) if len(signs) else 0.0

    penalty_parts = {
        "mean_shift_penalty": ramp_up_penalty(mean_shift_ratio, 0.35, 1.0, 30),
        "rolling_slope_penalty": ramp_up_penalty(rolling_slope_ratio, 0.30, 1.0, 25),
        "cusum_penalty": ramp_up_penalty(cusum_range, 0.18, 0.45, 20),
        "variance_shift_penalty": ramp_up_penalty(variance_shift_ratio, 0.60, 1.50, 15),
        "one_direction_penalty": ramp_up_penalty(sign_imbalance, 0.80, 1.0, 10),
    }
    penalty = sum(penalty_parts.values())

    reasons: list[str] = []
    if penalty_parts["mean_shift_penalty"] > 0:
        reasons.append("前后窗口均值偏移较明显，可能存在传感器基线漂移或长期环境趋势。")
    if penalty_parts["rolling_slope_penalty"] > 0:
        reasons.append("滚动均值呈持续单向变化，需复核设备校准、采样周期或真实农情变化。")
    if penalty_parts["cusum_penalty"] > 0:
        reasons.append("CUSUM 累积偏差较大，序列可能存在阶段性基线迁移。")
    if penalty_parts["variance_shift_penalty"] > 0:
        reasons.append("前后窗口方差变化较大，可能存在设备状态变化或采集条件改变。")
    if penalty_parts["one_direction_penalty"] > 0:
        reasons.append("相邻变化方向高度单一，长期单向漂移风险较高。")
    if not reasons:
        reasons.append("未发现明显传感器漂移信号；前后基线和滚动均值变化处于可解释范围。")

    chart = save_line_plot(values, f"传感器漂移扫描 - {series.name}", reports_dir, f"drift_{series.name}")
    return {
        "score": clamp_score(100 - penalty),
        "risk": "ok" if penalty < 30 else "attention",
        "reasons": reasons,
        "metrics": {
            "window_size": window,
            "head_mean": round(head_mean, 4),
            "tail_mean": round(tail_mean, 4),
            "mean_shift_ratio": round(mean_shift_ratio, 4),
            "rolling_slope_ratio": round(rolling_slope_ratio, 4),
            "cusum_range": round(cusum_range, 4),
            "variance_shift_ratio": round(variance_shift_ratio, 4),
            "sign_imbalance": round(sign_imbalance, 4),
            **{key: round(value, 4) for key, value in penalty_parts.items()},
        },
        "charts": [chart] if chart else [],
    }
