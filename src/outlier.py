from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .utils import clamp_score, clean_numeric, save_line_plot


def analyze_outliers(series: pd.Series, reports_dir: Path) -> dict:
    values = clean_numeric(series)
    if len(values) < 12:
        return {"score": 50.0, "risk": "insufficient_data", "reasons": ["样本过少，异常点分布判断不稳定。"], "metrics": {}, "charts": []}

    mean = float(values.mean())
    std = float(values.std(ddof=0)) or 1e-9
    z_outlier_rate = float((np.abs((values - mean) / std) > 3).mean())
    q1, q3 = values.quantile([0.25, 0.75])
    iqr = float(q3 - q1) or 1e-9
    iqr_outlier_rate = float(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).mean())

    contamination = min(0.15, max(0.02, 3 / len(values)))
    model = IsolationForest(contamination=contamination, random_state=42)
    iso_labels = model.fit_predict(values.to_numpy().reshape(-1, 1))
    isolation_rate = float((iso_labels == -1).mean())
    combined_rate = max(z_outlier_rate, iqr_outlier_rate, isolation_rate)
    natural_rule_rate = max(z_outlier_rate, iqr_outlier_rate)

    penalty = 0.0
    reasons: list[str] = []
    if natural_rule_rate == 0:
        penalty += 28
        reasons.append("z-score 和 IQR 均未检测到自然异常波动；长期完全规整也可能可疑。")
    elif combined_rate > 0.25:
        penalty += 24
        reasons.append("异常点比例偏高，可能存在采集故障、录入错误或拼接数据。")
    elif combined_rate < 0.02 and len(values) >= 50:
        penalty += 10
        reasons.append("异常波动很少，需结合业务场景确认是否过度清洗。")
    else:
        reasons.append("异常点比例处于可解释范围，存在一定自然波动。")

    if std / (abs(mean) + 1e-9) < 0.005:
        penalty += 16
        reasons.append("整体变异系数极低，异常波动不足。")

    chart = save_line_plot(values, f"Outlier scan - {series.name}", reports_dir, f"outlier_{series.name}")
    return {
        "score": clamp_score(100 - penalty),
        "risk": "ok" if penalty < 30 else "attention",
        "reasons": reasons,
        "metrics": {
            "z_outlier_rate": round(z_outlier_rate, 4),
            "iqr_outlier_rate": round(iqr_outlier_rate, 4),
            "isolation_forest_rate": round(isolation_rate, 4),
            "combined_outlier_rate": round(combined_rate, 4),
            "natural_rule_outlier_rate": round(natural_rule_rate, 4),
        },
        "charts": [chart] if chart else [],
    }
