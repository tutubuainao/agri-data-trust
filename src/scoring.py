from __future__ import annotations

from pathlib import Path

import pandas as pd

from .correlation import analyze_correlations
from .digit_analysis import analyze_digit_patterns
from .drift import analyze_sensor_drift
from .outlier import analyze_outliers
from .smoothness import analyze_smoothness
from .timeseries import analyze_timeseries_nature


COLUMN_INDICATORS = {
    "smoothness": ("平滑度检测", analyze_smoothness),
    "timeseries": ("时间序列自然性检测", analyze_timeseries_nature),
    "digit": ("小数位/数字规律检测", analyze_digit_patterns),
    "outlier": ("异常点分布检测", analyze_outliers),
    "drift": ("传感器漂移检测", analyze_sensor_drift),
}

INDICATOR_WEIGHTS = {
    "smoothness": 0.18,
    "timeseries": 0.18,
    "digit": 0.16,
    "outlier": 0.16,
    "drift": 0.14,
    "correlation": 0.18,
}


def risk_level(score: float) -> str:
    if score >= 70:
        return "低风险"
    if score >= 50:
        return "中风险"
    return "高风险"


def run_full_analysis(df: pd.DataFrame, numeric_columns: list[str], reports_dir: Path) -> dict:
    column_results: dict[str, dict] = {}
    indicator_scores: dict[str, list[float]] = {key: [] for key in COLUMN_INDICATORS}

    for col in numeric_columns:
        column_results[col] = {}
        for key, (label, analyzer) in COLUMN_INDICATORS.items():
            result = analyzer(df[col], reports_dir)
            result["label"] = label
            column_results[col][key] = result
            indicator_scores[key].append(float(result["score"]))

    correlation_result = analyze_correlations(df, numeric_columns, reports_dir)
    correlation_result["label"] = "多变量相关性检测"

    sub_scores = {
        key: round(sum(scores) / len(scores), 2) if scores else 50.0
        for key, scores in indicator_scores.items()
    }
    sub_scores["correlation"] = round(float(correlation_result["score"]), 2)

    total_score = round(sum(sub_scores[key] * INDICATOR_WEIGHTS[key] for key in INDICATOR_WEIGHTS), 2)
    reasons = collect_top_reasons(column_results, correlation_result)

    return {
        "total_score": total_score,
        "risk_level": risk_level(total_score),
        "sub_scores": sub_scores,
        "column_results": column_results,
        "correlation": correlation_result,
        "reasons": reasons,
    }


def collect_top_reasons(column_results: dict[str, dict], correlation_result: dict, limit: int = 10) -> list[str]:
    ranked: list[tuple[float, str]] = []
    for col, checks in column_results.items():
        for result in checks.values():
            score = float(result.get("score", 100))
            for reason in result.get("reasons", []):
                if "未发现" not in reason and "处于可解释范围" not in reason:
                    ranked.append((score, f"{col}: {reason}"))

    for reason in correlation_result.get("reasons", []):
        if "未发现" not in reason:
            ranked.append((float(correlation_result.get("score", 100)), reason))

    ranked.sort(key=lambda item: item[0])
    if not ranked:
        return ["未发现明显高风险模式。请结合采集设备、作物品类和业务规则继续复核。"]
    return [reason for _, reason in ranked[:limit]]


def sub_scores_dataframe(sub_scores: dict[str, float]) -> pd.DataFrame:
    labels = {
        "smoothness": "平滑度检测",
        "timeseries": "时间序列自然性检测",
        "digit": "小数位/数字规律检测",
        "outlier": "异常点分布检测",
        "drift": "传感器漂移检测",
        "correlation": "多变量相关性检测",
    }
    return pd.DataFrame(
        [{"指标": labels[key], "子评分": value, "风险等级": risk_level(value)} for key, value in sub_scores.items()]
    )
