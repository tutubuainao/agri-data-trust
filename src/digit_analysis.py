from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from .utils import clamp_score, clean_numeric, ramp_up_penalty, save_bar_plot


COUNT_COLUMN_HINTS = (
    "卵块",
    "卵粒",
    "幼虫",
    "成虫",
    "虫量",
    "诱捕",
    "孵化",
    "寄生",
    "干瘪",
    "出蜂",
    "株数",
    "数量",
    "头数",
    "粒数",
    "个数",
    "只数",
    "count",
    "number",
    "quantity",
    "qty",
)

RATE_COLUMN_HINTS = ("率", "比例", "percent", "percentage", "rate")

MEASUREMENT_COLUMN_HINTS = (
    "温度",
    "湿度",
    "水分",
    "墒情",
    "降雨",
    "雨量",
    "残留",
    "浓度",
    "含量",
    "产量",
    "重量",
    "质量",
    "株高",
    "高度",
    "长度",
    "面积",
    "ph",
    "ec",
    "temp",
    "temperature",
    "humidity",
    "rain",
    "yield",
    "residue",
    "concentration",
    "weight",
    "height",
    "area",
)


def _decimal_places(value: float) -> int:
    text = f"{value:.10f}".rstrip("0").rstrip(".")
    return len(text.split(".")[1]) if "." in text else 0


def _last_digit(value: float) -> int:
    places = _decimal_places(value)
    scaled = int(round(abs(value) * (10**places)))
    return scaled % 10


def _integer_digit_length(value: float) -> int:
    integer = int(abs(round(value)))
    return max(1, len(str(integer)))


def _integer_digit_length_counts(values: pd.Series) -> Counter:
    integer_values = values[np.isclose(values % 1, 0)]
    return Counter(_integer_digit_length(float(x)) for x in integer_values)


def _numeric_kind(column: object, values: pd.Series, integer_rate: float, duplicate_rate: float) -> str:
    name = str(column).strip().lower()
    if any(hint.lower() in name for hint in RATE_COLUMN_HINTS):
        return "rate_or_ratio"
    if integer_rate < 0.9 or float(values.min()) < 0:
        return "continuous_or_unknown"

    has_count_name = any(hint.lower() in name for hint in COUNT_COLUMN_HINTS)
    if has_count_name:
        return "count"
    has_measurement_name = any(hint.lower() in name for hint in MEASUREMENT_COLUMN_HINTS)
    if has_measurement_name:
        return "rounded_measurement"

    length_counts = _integer_digit_length_counts(values)
    length_diversity = len(length_counts)
    unique_count = values.nunique(dropna=True)
    min_unique_for_discrete = min(8, max(3, int(len(values) * 0.15)))
    if length_diversity >= 2 and unique_count >= min_unique_for_discrete and duplicate_rate < 0.9:
        return "discrete_integer"
    return "continuous_or_unknown"


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
    digit_length_counts = _integer_digit_length_counts(values)
    dominant_digit_length_rate = max(digit_length_counts.values()) / len(values) if digit_length_counts else 0.0
    digit_length_diversity = len(digit_length_counts)
    numeric_kind = _numeric_kind(series.name, values, integer_rate, duplicate_rate)
    integer_like = numeric_kind in {"count", "discrete_integer"}
    small_integer_scale = integer_like and float(values.abs().max()) < 10

    if integer_like:
        if small_integer_scale:
            last_digit_penalty = 0.0
        elif numeric_kind == "count":
            last_digit_penalty = ramp_up_penalty(dominant_last_digit_rate, 0.75, 0.98, 8)
        else:
            last_digit_penalty = ramp_up_penalty(dominant_last_digit_rate, 0.70, 0.98, 10)
        penalty_parts = {
            "integer_penalty": 0.0,
            "decimal_place_penalty": 0.0,
            "last_digit_penalty": last_digit_penalty,
            "rounded_0_05_penalty": 0.0,
            "duplicate_penalty": ramp_up_penalty(
                duplicate_rate,
                0.92 if numeric_kind == "count" else 0.85,
                1.0,
                6 if numeric_kind == "count" else 8,
            ),
        }
    elif numeric_kind == "rounded_measurement":
        penalty_parts = {
            "integer_penalty": ramp_up_penalty(integer_rate, 0.85, 1.0, 8),
            "decimal_place_penalty": ramp_up_penalty(dominant_decimal_rate, 0.92, 1.0, 6),
            "last_digit_penalty": ramp_up_penalty(dominant_last_digit_rate, 0.45, 1.0, 10),
            "rounded_0_05_penalty": ramp_up_penalty(rounded_05_rate, 0.9, 1.0, 4),
            "duplicate_penalty": ramp_up_penalty(duplicate_rate, 0.55, 1.0, 10),
        }
    else:
        penalty_parts = {
            "integer_penalty": ramp_up_penalty(integer_rate, 0.75, 1.0, 24),
            "decimal_place_penalty": ramp_up_penalty(dominant_decimal_rate, 0.9, 1.0, 20),
            "last_digit_penalty": ramp_up_penalty(dominant_last_digit_rate, 0.35, 1.0, 18),
            "rounded_0_05_penalty": ramp_up_penalty(rounded_05_rate, 0.8, 1.0, 16),
            "duplicate_penalty": ramp_up_penalty(duplicate_rate, 0.45, 1.0, 12),
        }
    penalty = sum(penalty_parts.values())
    reasons: list[str] = []
    if numeric_kind == "count":
        reasons.append("该列识别为计数型整数指标，整数比例和小数位一致属于正常采集特征，已按计数型规则降权处理。")
    elif numeric_kind == "discrete_integer":
        reasons.append("该列识别为多位数离散整数序列，整数位数跨度属于计数或等级型数据的常见现象，已降低整数比例和小数位一致带来的扣分。")
    elif numeric_kind == "rounded_measurement":
        reasons.append("该列名称像连续测量指标，但数值以整数记录；系统按低精度测量规则轻度扣分，并主要结合平滑度和异常波动继续判断。")
    if integer_like and digit_length_diversity >= 2:
        shown_lengths = "、".join(f"{length}位" for length in sorted(digit_length_counts))
        reasons.append(f"整数位数包含 {shown_lengths}，系统会重点看重复值和尾数是否过度集中，而不是简单因为全是整数扣分。")
    if penalty_parts["integer_penalty"] > 0:
        reasons.append("整数比例过高，连续传感器数据通常会保留一定小数波动。")
    if penalty_parts["decimal_place_penalty"] > 0:
        reasons.append("小数位数量高度一致，数据可能经过统一格式化或人工整理。")
    if penalty_parts["last_digit_penalty"] > 0:
        reasons.append("末位数字分布集中，存在数字规律偏强的风险。")
    elif small_integer_scale:
        reasons.append("该列为小范围整数，末位数字本身等同于取值类别，已避免按尾数分布误判。")
    if penalty_parts["rounded_0_05_penalty"] > 0:
        reasons.append("大量数值落在 0.05 的倍数上，数值过于整齐。")
    if penalty_parts["duplicate_penalty"] > 0:
        if integer_like:
            reasons.append("离散整数值重复比例极高，建议确认是否存在默认填充值、漏录或批量复制。")
        else:
            reasons.append("重复数值比例偏高，可能缺少自然测量噪声。")

    if not reasons:
        reasons.append("小数位、末位数字和重复值分布未发现明显过度整齐特征。")

    chart = save_bar_plot(
        [str(i) for i in range(10)],
        [last_digit_counts.get(i, 0) for i in range(10)],
        f"末位数字分布 - {series.name}",
        reports_dir,
        f"digits_{series.name}",
    )
    return {
        "score": clamp_score(100 - penalty),
        "risk": "ok" if penalty < 30 else "attention",
        "reasons": reasons,
        "metrics": {
            "numeric_kind": numeric_kind,
            "integer_rate": round(integer_rate, 4),
            "dominant_decimal_place_rate": round(dominant_decimal_rate, 4),
            "dominant_last_digit_rate": round(dominant_last_digit_rate, 4),
            "digit_length_diversity": digit_length_diversity,
            "dominant_digit_length_rate": round(dominant_digit_length_rate, 4),
            "digit_length_counts": dict(sorted(digit_length_counts.items())),
            "rounded_0_05_rate": round(rounded_05_rate, 4),
            "duplicate_rate": round(duplicate_rate, 4),
            **{key: round(value, 4) for key, value in penalty_parts.items()},
        },
        "charts": [chart] if chart else [],
    }
