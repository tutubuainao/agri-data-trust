from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from .utils import clamp_score, clean_numeric, save_bar_plot


def _decimal_places(value: float) -> int:
    text = f"{value:.10f}".rstrip("0").rstrip(".")
    return len(text.split(".")[1]) if "." in text else 0


def _last_digit(value: float) -> int:
    scaled = int(round(abs(value) * 100))
    return scaled % 10


def analyze_digit_patterns(series: pd.Series, reports_dir: Path) -> dict:
    values = clean_numeric(series)
    if len(values) < 10:
        return {"score": 50.0, "risk": "insufficient_data", "reasons": ["样本过少，数字规律判断不稳定。"], "metrics": {}, "charts": []}

    integer_rate = float(np.isclose(values % 1, 0).mean())
    decimal_counts = Counter(_decimal_places(float(x)) for x in values)
    dominant_decimal_rate = max(decimal_counts.values()) / len(values)
    last_digits = [_last_digit(float(x)) for x in values]
    last_digit_counts = Counter(last_digits)
    dominant_last_digit_rate = max(last_digit_counts.values()) / len(values)
    rounded_05_rate = float(np.isclose((values * 20) % 1, 0).mean())
    duplicate_rate = 1 - values.nunique(dropna=True) / len(values)

    penalty = 0.0
    reasons: list[str] = []
    if integer_rate > 0.75:
        penalty += 24
        reasons.append("整数比例过高，连续传感器数据通常会保留一定小数波动。")
    if dominant_decimal_rate > 0.9:
        penalty += 20
        reasons.append("小数位数量高度一致，数据可能经过统一格式化或人工整理。")
    if dominant_last_digit_rate > 0.35:
        penalty += 18
        reasons.append("尾数分布集中，存在数字规律偏强的风险。")
    if rounded_05_rate > 0.8:
        penalty += 16
        reasons.append("大量数值落在 0.05 的倍数上，数值过于整齐。")
    if duplicate_rate > 0.45:
        penalty += 12
        reasons.append("重复数值比例偏高，可能缺少自然测量噪声。")

    if not reasons:
        reasons.append("小数位、尾数和重复值分布未发现明显过度整齐特征。")

    chart = save_bar_plot([str(i) for i in range(10)], [last_digit_counts.get(i, 0) for i in range(10)], f"Last digit distribution - {series.name}", reports_dir, f"digits_{series.name}")
    return {
        "score": clamp_score(100 - penalty),
        "risk": "ok" if penalty < 30 else "attention",
        "reasons": reasons,
        "metrics": {
            "integer_rate": round(integer_rate, 4),
            "dominant_decimal_place_rate": round(dominant_decimal_rate, 4),
            "dominant_last_digit_rate": round(dominant_last_digit_rate, 4),
            "rounded_0_05_rate": round(rounded_05_rate, 4),
            "duplicate_rate": round(duplicate_rate, 4),
        },
        "charts": [chart] if chart else [],
    }
