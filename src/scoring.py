from __future__ import annotations

from pathlib import Path

import pandas as pd

from .changepoint import analyze_changepoints
from .correlation import analyze_correlations
from .digit_analysis import analyze_digit_patterns
from .drift import analyze_sensor_drift
from .outlier import analyze_outliers
from .physical_rules import analyze_physical_rules
from .profiler import DataProfile
from .sampling_integrity import analyze_sampling_integrity
from .smoothness import analyze_smoothness
from .timeseries import analyze_timeseries_nature


COLUMN_INDICATORS = {
    "smoothness": ("平滑度检测", analyze_smoothness),
    "timeseries": ("时间序列自然性检测", analyze_timeseries_nature),
    "digit": ("小数位/数字规律检测", analyze_digit_patterns),
    "outlier": ("异常点分布检测", analyze_outliers),
    "drift": ("传感器漂移检测", analyze_sensor_drift),
    "changepoint": ("变化点检测", analyze_changepoints),
}

DEFAULT_INDICATOR_WEIGHTS = {
    "smoothness": 0.18,
    "timeseries": 0.16,
    "digit": 0.13,
    "outlier": 0.06,
    "drift": 0.14,
    "changepoint": 0.06,
    "sampling": 0.04,
    "physical": 0.04,
    "correlation": 0.19,
}

SCENARIO_INDICATOR_WEIGHTS = {
    "auto": DEFAULT_INDICATOR_WEIGHTS,
    "greenhouse": {
        "smoothness": 0.16,
        "timeseries": 0.18,
        "digit": 0.08,
        "outlier": 0.08,
        "drift": 0.16,
        "changepoint": 0.10,
        "sampling": 0.08,
        "physical": 0.06,
        "correlation": 0.10,
    },
    "pest": {
        "smoothness": 0.10,
        "timeseries": 0.08,
        "digit": 0.14,
        "outlier": 0.12,
        "drift": 0.08,
        "changepoint": 0.14,
        "sampling": 0.08,
        "physical": 0.14,
        "correlation": 0.12,
    },
    "yield": {
        "smoothness": 0.10,
        "timeseries": 0.08,
        "digit": 0.12,
        "outlier": 0.12,
        "drift": 0.08,
        "changepoint": 0.10,
        "sampling": 0.10,
        "physical": 0.14,
        "correlation": 0.16,
    },
    "residue": {
        "smoothness": 0.08,
        "timeseries": 0.06,
        "digit": 0.16,
        "outlier": 0.12,
        "drift": 0.06,
        "changepoint": 0.10,
        "sampling": 0.08,
        "physical": 0.20,
        "correlation": 0.14,
    },
}


def indicator_weights_for_scenario(scenario: str | None) -> dict[str, float]:
    return dict(SCENARIO_INDICATOR_WEIGHTS.get(scenario or "auto", DEFAULT_INDICATOR_WEIGHTS))


def risk_level(score: float) -> str:
    if score >= 70:
        return "低风险"
    if score >= 50:
        return "中风险"
    return "高风险"


def run_full_analysis(
    df: pd.DataFrame,
    profile: DataProfile,
    reports_dir: Path,
    scenario: str | None = "auto",
) -> dict:
    numeric_columns = profile.numeric_columns
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
    sampling_result = analyze_sampling_integrity(df, profile)
    sampling_result["label"] = "采样完整性检测"
    physical_result = analyze_physical_rules(df, numeric_columns, scenario)
    physical_result["label"] = "物理范围与单位检测"

    column_sub_scores = {
        key: round(sum(scores) / len(scores), 2) if scores else 50.0
        for key, scores in indicator_scores.items()
    }
    sub_scores = {
        **column_sub_scores,
        "sampling": round(float(sampling_result["score"]), 2),
        "physical": round(float(physical_result["score"]), 2),
        "correlation": round(float(correlation_result["score"]), 2),
    }

    weights = indicator_weights_for_scenario(scenario)
    total_score = round(sum(sub_scores[key] * weights[key] for key in weights), 2)
    dataset_results = {
        "sampling": sampling_result,
        "physical": physical_result,
    }
    reasons = collect_top_reasons(column_results, correlation_result, dataset_results)

    return {
        "total_score": total_score,
        "risk_level": risk_level(total_score),
        "weights": weights,
        "sub_scores": sub_scores,
        "column_results": column_results,
        "dataset_results": dataset_results,
        "correlation": correlation_result,
        "reasons": reasons,
    }


def collect_top_reasons(
    column_results: dict[str, dict],
    correlation_result: dict,
    dataset_results: dict[str, dict] | None = None,
    limit: int = 12,
) -> list[str]:
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

    for result in (dataset_results or {}).values():
        score = float(result.get("score", 100))
        label = result.get("label", "数据集检测")
        for reason in result.get("reasons", []):
            if "未发现" not in reason and "未识别" not in reason:
                ranked.append((score, f"{label}: {reason}"))

    ranked.sort(key=lambda item: item[0])
    if not ranked:
        return ["未发现明显高风险模式。请结合采集设备、作物品类和业务规则继续复核。"]
    return [reason for _, reason in ranked[:limit]]


def sub_scores_dataframe(sub_scores: dict[str, float], weights: dict[str, float] | None = None) -> pd.DataFrame:
    labels = {
        "smoothness": "平滑度检测",
        "timeseries": "时间序列自然性检测",
        "digit": "小数位/数字规律检测",
        "outlier": "异常点分布检测",
        "drift": "传感器漂移检测",
        "changepoint": "变化点检测",
        "sampling": "采样完整性检测",
        "physical": "物理范围与单位检测",
        "correlation": "多变量相关性检测",
    }
    rows = []
    for key, value in sub_scores.items():
        row = {"指标": labels[key], "子评分": value, "风险等级": risk_level(value)}
        if weights is not None:
            row["当前权重"] = f"{weights.get(key, 0) * 100:.0f}%"
        rows.append(row)
    return pd.DataFrame(
        rows
    )
