from __future__ import annotations

import pandas as pd

from .rule_config import match_rule, scenario_info
from .utils import clamp_score, clean_numeric, ramp_up_penalty


def analyze_physical_rules(df: pd.DataFrame, numeric_columns: list[str], scenario: str | None = "auto") -> dict:
    info = scenario_info(scenario)
    reasons: list[str] = []
    matched_rules: list[dict[str, object]] = []
    penalty = 0.0

    for col in numeric_columns:
        rule = match_rule(col, info["key"])
        if rule is None:
            continue
        values = clean_numeric(df[col])
        if values.empty:
            continue

        hard_bad = pd.Series(False, index=values.index)
        soft_bad = pd.Series(False, index=values.index)
        if rule.hard_min is not None:
            hard_bad = hard_bad | (values < rule.hard_min)
            soft_bad = soft_bad | (values < rule.soft_min) if rule.soft_min is not None else soft_bad
        if rule.hard_max is not None:
            hard_bad = hard_bad | (values > rule.hard_max)
            soft_bad = soft_bad | (values > rule.soft_max) if rule.soft_max is not None else soft_bad

        hard_rate = float(hard_bad.mean())
        soft_rate = float((soft_bad & ~hard_bad).mean())
        hard_penalty = ramp_up_penalty(hard_rate, 0.0, 0.15, 28)
        soft_penalty = ramp_up_penalty(soft_rate, 0.02, 0.30, 16)
        unit_penalty = 0.0

        max_value = float(values.max())
        min_value = float(values.min())
        if rule.key in {"humidity", "soil_moisture"} and 0 <= min_value and max_value <= 1:
            unit_penalty = 6.0
            reasons.append(f"{col}: 数值落在 0-1 区间，字段名称像百分比指标，需确认单位是否为比例而不是百分数。")
        if rule.key == "pesticide_residue" and min_value < 0:
            unit_penalty = max(unit_penalty, 10.0)
        if "率" in str(col) and max_value <= 1 and min_value >= 0:
            unit_penalty = max(unit_penalty, 4.0)

        penalty += hard_penalty + soft_penalty + unit_penalty
        matched_rules.append(
            {
                "column": str(col),
                "rule": rule.label,
                "soft_min": rule.soft_min,
                "soft_max": rule.soft_max,
                "hard_min": rule.hard_min,
                "hard_max": rule.hard_max,
                "min": round(min_value, 4),
                "max": round(max_value, 4),
                "hard_out_of_range_rate": round(hard_rate, 4),
                "soft_out_of_range_rate": round(soft_rate, 4),
                "unit_note": rule.unit_note,
            }
        )
        if hard_penalty > 0:
            reasons.append(f"{col}: 出现超出物理硬范围的数值，需优先复核单位、量纲或录入错误。")
        if soft_penalty > 0:
            reasons.append(f"{col}: 部分数值超出常见农业经验范围，建议结合地区、作物和设备规格复核。")

    coverage = len(matched_rules) / max(len(numeric_columns), 1)
    coverage_penalty = 8.0 if numeric_columns and coverage < 0.25 else 0.0
    penalty += coverage_penalty
    if coverage_penalty:
        reasons.append("可匹配到物理规则的字段较少，建议选择更贴近数据类型的场景或补充字段名称。")
    if not reasons:
        reasons.append("已匹配字段未发现明显物理范围或单位异常。")

    return {
        "score": clamp_score(100 - penalty),
        "risk": "ok" if penalty < 30 else "attention",
        "reasons": reasons,
        "metrics": {
            "scenario": info["key"],
            "scenario_label": info["label"],
            "matched_rule_count": len(matched_rules),
            "rule_coverage": round(coverage, 4),
            "coverage_penalty": round(coverage_penalty, 4),
            "matched_rules": matched_rules,
        },
        "charts": [],
    }
