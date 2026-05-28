from __future__ import annotations

from pathlib import Path

import pandas as pd

from .changepoint import analyze_changepoints
from .correlation import analyze_correlations
from .digit_analysis import analyze_digit_patterns
from .drift import analyze_sensor_drift
from .indicator_config import (
    ALL_INDICATORS,
    available_indicator_payload,
    resolve_indicator_selection,
    weights_for_selection,
)
from .ml_detection import analyze_ml_anomaly
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

CORE_GUARDRAIL_INDICATORS = ("smoothness", "digit", "outlier", "physical")

def indicator_weights_for_scenario(
    scenario: str | None,
    indicators: list[str] | None = None,
) -> dict[str, float]:
    return weights_for_selection(scenario, indicators)


def risk_level(score: float) -> str:
    if score >= 70:
        return "低风险"
    if score >= 50:
        return "中风险"
    return "高风险"


def apply_core_score_guardrail(
    total_score: float,
    sub_scores: dict[str, float],
    selected_indicators: list[str],
) -> tuple[float, str | None]:
    core_scores = [
        float(sub_scores[key])
        for key in CORE_GUARDRAIL_INDICATORS
        if key in selected_indicators and key in sub_scores
    ]
    if not core_scores:
        return total_score, None
    min_core = min(core_scores)
    if min_core < 35 and total_score > 59.99:
        return 59.99, "存在默认核心指标低于 35 分，总分上限调整为 59.99，避免单项严重风险被其他高分完全抵消。"
    if min_core < 50 and total_score > 69.99:
        return 69.99, "存在默认核心指标低于 50 分，总分上限调整为 69.99，避免单项高风险被其他高分完全抵消。"
    return total_score, None


def run_full_analysis(
    df: pd.DataFrame,
    profile: DataProfile,
    reports_dir: Path,
    scenario: str | None = "auto",
    indicators: list[str] | str | None = None,
    custom_indicators: bool = False,
) -> dict:
    numeric_columns = profile.numeric_columns
    selection = resolve_indicator_selection(scenario, indicators, custom_indicators)
    selected_indicators: list[str] = selection["selected"]
    selected_column_indicators = [
        key for key in selected_indicators if key in COLUMN_INDICATORS
    ]
    column_results: dict[str, dict] = {}
    indicator_scores: dict[str, list[float]] = {key: [] for key in selected_column_indicators}

    for col in numeric_columns:
        column_results[col] = {}
        for key in selected_column_indicators:
            label, analyzer = COLUMN_INDICATORS[key]
            result = analyzer(df[col], reports_dir)
            result["label"] = label
            column_results[col][key] = result
            indicator_scores[key].append(float(result["score"]))

    column_sub_scores = {
        key: round(sum(scores) / len(scores), 2) if scores else 50.0
        for key, scores in indicator_scores.items()
    }
    sub_scores = dict(column_sub_scores)
    dataset_results: dict[str, dict] = {}

    if "sampling" in selected_indicators:
        sampling_result = analyze_sampling_integrity(df, profile)
        sampling_result["label"] = "采样完整性检测"
        dataset_results["sampling"] = sampling_result
        sub_scores["sampling"] = round(float(sampling_result["score"]), 2)

    if "physical" in selected_indicators:
        physical_result = analyze_physical_rules(df, numeric_columns, scenario)
        physical_result["label"] = "有效性/物理范围与单位检测"
        dataset_results["physical"] = physical_result
        sub_scores["physical"] = round(float(physical_result["score"]), 2)

    if "ml_anomaly" in selected_indicators:
        ml_result = analyze_ml_anomaly(df, numeric_columns, reports_dir)
        ml_result["label"] = "机器学习异常识别"
        dataset_results["ml_anomaly"] = ml_result
        sub_scores["ml_anomaly"] = round(float(ml_result["score"]), 2)

    if "correlation" in selected_indicators:
        correlation_result = analyze_correlations(df, numeric_columns, reports_dir)
        correlation_result["label"] = "多变量相关性检测"
        sub_scores["correlation"] = round(float(correlation_result["score"]), 2)
    else:
        correlation_result = {
            "label": "多变量相关性检测",
            "score": None,
            "risk": "skipped",
            "reasons": ["当前未选择多变量相关性检测。"],
            "metrics": {},
            "charts": [],
            "skipped": True,
        }

    weights = weights_for_selection(scenario, selected_indicators)
    raw_total_score = round(
        sum(sub_scores[key] * weights[key] for key in weights if key in sub_scores),
        2,
    )
    total_score, guardrail_reason = apply_core_score_guardrail(
        raw_total_score,
        sub_scores,
        selected_indicators,
    )
    total_score = round(total_score, 2)
    selected_payload = {
        "mode": selection["mode"],
        "selected": selected_indicators,
        "available": available_indicator_payload(),
        "default_core": selection["default_core"],
        "optional": selection["optional"],
    }
    reasons = collect_top_reasons(column_results, correlation_result, dataset_results)
    if guardrail_reason:
        reasons.insert(0, guardrail_reason)

    return {
        "total_score": total_score,
        "raw_total_score": raw_total_score,
        "score_adjustment": guardrail_reason,
        "risk_level": risk_level(total_score),
        "weights": weights,
        "sub_scores": sub_scores,
        "indicator_selection": selected_payload,
        "selected_indicators": selected_indicators,
        "available_indicators": selected_payload["available"],
        "indicator_selection_mode": selection["mode"],
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

    for reason in (correlation_result or {}).get("reasons", []):
        if "未发现" not in reason and "未选择" not in reason:
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
        "physical": "有效性/物理范围与单位检测",
        "correlation": "多变量相关性检测",
        "ml_anomaly": "机器学习异常识别",
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
