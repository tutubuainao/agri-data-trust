from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler
from sklearn.svm import OneClassSVM

from .utils import clamp_score, ramp_down_penalty, ramp_up_penalty, save_bar_plot


MIN_ROWS = 20
MIN_FEATURES = 2
MAX_MODEL_ROWS = 800
RANDOM_STATE = 42


def _usable_numeric_frame(df: pd.DataFrame, numeric_columns: list[str]) -> tuple[pd.DataFrame, list[str]]:
    usable: dict[str, pd.Series] = {}
    skipped: list[str] = []
    row_count = len(df)
    min_non_null = max(10, int(row_count * 0.4))

    for column in numeric_columns:
        values = pd.to_numeric(df[column], errors="coerce")
        non_null = int(values.notna().sum())
        unique_count = int(values.dropna().nunique())
        if non_null < min_non_null:
            skipped.append(f"{column} 有效数值过少，未进入机器学习特征。")
            continue
        if unique_count < 3:
            skipped.append(f"{column} 有效唯一值少于 3 个，未进入机器学习特征。")
            continue
        usable[column] = values.astype(float)

    frame = pd.DataFrame(usable).dropna(how="all")
    return frame, skipped


def _prepare_matrix(frame: pd.DataFrame) -> np.ndarray:
    imputed = SimpleImputer(strategy="median").fit_transform(frame)
    return RobustScaler().fit_transform(imputed)


def _predict_safely(name: str, estimator, matrix: np.ndarray) -> tuple[str, np.ndarray | None, str | None]:
    try:
        labels = estimator.fit_predict(matrix)
        return name, np.asarray(labels), None
    except Exception as exc:  # pragma: no cover - estimator failures depend on sklearn internals
        return name, None, f"{name} 模型执行失败，已跳过该模型：{exc}"


def analyze_ml_anomaly(df: pd.DataFrame, numeric_columns: list[str], reports_dir: Path) -> dict:
    """Dataset-level unsupervised ML anomaly signal.

    This is an optional scoring indicator. It does not train a truth/fake classifier;
    it checks whether multiple classical anomaly detectors agree on suspicious rows.
    """
    frame, skipped_features = _usable_numeric_frame(df, numeric_columns)
    if len(frame) < MIN_ROWS:
        return {
            "score": 55.0,
            "risk": "insufficient_data",
            "reasons": ["可用于机器学习异常识别的样本少于 20 行，模型结果不稳定，已降级为提示项。"],
            "metrics": {
                "usable_rows": int(len(frame)),
                "usable_features": int(frame.shape[1]),
                "skipped_features": skipped_features,
            },
            "charts": [],
        }

    if frame.shape[1] < MIN_FEATURES:
        return {
            "score": 58.0,
            "risk": "insufficient_features",
            "reasons": ["机器学习异常识别至少需要 2 个有效数值特征；单列数据建议主要查看异常点分布指标。"],
            "metrics": {
                "usable_rows": int(len(frame)),
                "usable_features": int(frame.shape[1]),
                "skipped_features": skipped_features,
            },
            "charts": [],
        }

    sampled = frame
    if len(frame) > MAX_MODEL_ROWS:
        sampled = frame.sample(MAX_MODEL_ROWS, random_state=RANDOM_STATE)

    matrix = _prepare_matrix(sampled)
    row_count = matrix.shape[0]
    contamination = min(0.12, max(0.02, 8.0 / row_count))
    neighbors = min(20, max(5, int(np.sqrt(row_count))))
    neighbors = min(neighbors, row_count - 1)

    models = [
        (
            "IsolationForest",
            IsolationForest(
                n_estimators=160,
                contamination=contamination,
                random_state=RANDOM_STATE,
            ),
        ),
        (
            "LocalOutlierFactor",
            LocalOutlierFactor(
                n_neighbors=neighbors,
                contamination=contamination,
            ),
        ),
        (
            "OneClassSVM",
            OneClassSVM(
                kernel="rbf",
                gamma="scale",
                nu=contamination,
            ),
        ),
    ]

    model_labels: dict[str, np.ndarray] = {}
    model_warnings: list[str] = []
    for name, estimator in models:
        model_name, labels, warning = _predict_safely(name, estimator, matrix)
        if labels is not None:
            model_labels[model_name] = labels
        if warning:
            model_warnings.append(warning)

    if len(model_labels) < 2:
        return {
            "score": 55.0,
            "risk": "model_unavailable",
            "reasons": ["机器学习模型可用数量不足，无法形成稳定集成判断。", *model_warnings],
            "metrics": {
                "usable_rows": int(len(frame)),
                "sampled_rows": int(row_count),
                "usable_features": int(frame.shape[1]),
                "skipped_features": skipped_features,
                "model_warnings": model_warnings,
            },
            "charts": [],
        }

    anomaly_flags = {name: labels == -1 for name, labels in model_labels.items()}
    votes = np.vstack([flags.astype(int) for flags in anomaly_flags.values()]).sum(axis=0)
    consensus_threshold = max(2, int(np.ceil(len(anomaly_flags) * 0.66)))
    consensus_rate = float((votes >= consensus_threshold).mean())
    any_model_rate = float((votes >= 1).mean())
    model_rates = {name: float(flags.mean()) for name, flags in anomaly_flags.items()}
    rate_values = list(model_rates.values())
    max_model_rate = max(rate_values)
    rate_spread = max(rate_values) - min(rate_values)
    full_agreement_rate = float(((votes == 0) | (votes == len(anomaly_flags))).mean())
    disagreement_rate = 1.0 - full_agreement_rate

    penalty_parts = {
        "consensus_anomaly_penalty": ramp_up_penalty(consensus_rate, 0.08, 0.25, 35),
        "single_model_high_rate_penalty": ramp_up_penalty(max_model_rate, 0.20, 0.45, 18),
        "model_disagreement_penalty": ramp_up_penalty(disagreement_rate, 0.35, 0.75, 12),
        "rate_spread_penalty": ramp_up_penalty(rate_spread, 0.12, 0.35, 10),
        "small_sample_penalty": ramp_down_penalty(row_count, 50, 20, 10),
    }
    penalty = sum(penalty_parts.values())
    score = clamp_score(100 - penalty)

    reasons: list[str] = []
    if penalty_parts["consensus_anomaly_penalty"] > 0:
        reasons.append("多个机器学习模型共同识别出较高比例的可疑样本，建议复核这些行对应的采集记录。")
    if penalty_parts["single_model_high_rate_penalty"] > 0:
        reasons.append("至少一个机器学习模型给出了偏高异常比例，可能存在局部离群、拼接或多变量关系异常。")
    if penalty_parts["model_disagreement_penalty"] > 0:
        reasons.append("不同机器学习模型判断分歧较大，说明数据分布边界不稳定，建议结合传统指标一起复核。")
    if penalty_parts["small_sample_penalty"] > 0:
        reasons.append("机器学习有效样本量偏少，结果只能作为辅助线索。")
    reasons.extend(model_warnings)
    if not reasons:
        reasons.append("机器学习模型未发现明显集中的多变量异常样本。")

    chart_labels = list(model_rates.keys()) + ["模型共识", "任一模型"]
    chart_values = [round(model_rates[name] * 100, 2) for name in model_rates]
    chart_values.extend([round(consensus_rate * 100, 2), round(any_model_rate * 100, 2)])
    chart = save_bar_plot(
        chart_labels,
        chart_values,
        "机器学习异常样本比例（%）",
        reports_dir,
        "ml_anomaly_rates",
    )

    return {
        "score": score,
        "risk": "ok" if penalty < 25 else "attention",
        "reasons": reasons,
        "metrics": {
            "usable_rows": int(len(frame)),
            "sampled_rows": int(row_count),
            "usable_features": int(frame.shape[1]),
            "contamination": round(contamination, 4),
            "consensus_anomaly_rate": round(consensus_rate, 4),
            "any_model_anomaly_rate": round(any_model_rate, 4),
            "model_disagreement_rate": round(disagreement_rate, 4),
            "model_rate_spread": round(rate_spread, 4),
            "skipped_features": skipped_features,
            "model_warnings": model_warnings,
            **{key: round(value, 4) for key, value in model_rates.items()},
            **{key: round(value, 4) for key, value in penalty_parts.items()},
        },
        "charts": [chart] if chart else [],
    }
