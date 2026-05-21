from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf

from .utils import clamp_score, clean_numeric, save_bar_plot


def analyze_timeseries_nature(series: pd.Series, reports_dir: Path) -> dict:
    values = clean_numeric(series)
    if len(values) < 12:
        return {"score": 50.0, "risk": "insufficient_data", "reasons": ["样本过少，时间序列自然性判断不稳定。"], "metrics": {}, "charts": []}

    centered = values - values.mean()
    acf_values = acf(centered, nlags=min(12, len(values) // 2), fft=False, missing="drop")
    lag1 = float(acf_values[1]) if len(acf_values) > 1 else 0.0
    lag2 = float(acf_values[2]) if len(acf_values) > 2 else 0.0
    diffs = values.diff().dropna()
    sign_changes = int(np.sum(np.diff(np.sign(diffs.to_numpy())) != 0)) if len(diffs) > 1 else 0
    sign_change_rate = sign_changes / max(len(diffs) - 1, 1)
    trend_strength = abs(float(np.corrcoef(np.arange(len(values)), values.to_numpy())[0, 1])) if len(values) > 2 else 0.0

    penalty = 0.0
    reasons: list[str] = []
    if lag1 > 0.98:
        penalty += 22
        reasons.append("lag-1 autocorrelation 接近 1，可能呈现机械式连续变化。")
    elif lag1 < -0.2:
        penalty += 10
        reasons.append("lag-1 autocorrelation 为明显负值，需关注是否存在人为交替模式。")
    if sign_change_rate < 0.08:
        penalty += 20
        reasons.append("趋势方向变化很少，序列可能缺少真实环境中的短期扰动。")
    if trend_strength > 0.97 and sign_change_rate < 0.18:
        penalty += 18
        reasons.append("整体趋势近似完美线性，农业采集数据通常不会完全如此规整。")
    if max(abs(x) for x in acf_values[2:]) < 0.05 and len(values) >= 20:
        penalty += 10
        reasons.append("高阶 ACF 几乎全部接近 0，时间相关结构偏弱。")

    if not reasons:
        reasons.append("序列存在可解释的时间相关性和趋势变化，未发现明显机械模式。")

    chart = save_bar_plot([f"lag{i}" for i in range(len(acf_values))], [float(x) for x in acf_values], f"ACF - {series.name}", reports_dir, f"acf_{series.name}")
    return {
        "score": clamp_score(100 - penalty),
        "risk": "ok" if penalty < 30 else "attention",
        "reasons": reasons,
        "metrics": {
            "acf_lag1": round(lag1, 4),
            "acf_lag2": round(lag2, 4),
            "sign_change_rate": round(sign_change_rate, 4),
            "trend_strength": round(trend_strength, 4),
        },
        "charts": [chart] if chart else [],
    }
