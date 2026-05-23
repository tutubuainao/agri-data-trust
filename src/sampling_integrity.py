from __future__ import annotations

import numpy as np
import pandas as pd

from .loader import SHEET_COLUMN
from .profiler import DataProfile
from .utils import clamp_score, ramp_up_penalty


def _sheet_structure_mismatch(df: pd.DataFrame) -> float:
    if SHEET_COLUMN not in df.columns or df[SHEET_COLUMN].nunique(dropna=True) <= 1:
        return 0.0

    sheet_sets: list[set[str]] = []
    value_columns = [col for col in df.columns if col != SHEET_COLUMN]
    for _, group in df.groupby(SHEET_COLUMN, dropna=True):
        present = {str(col) for col in value_columns if group[col].notna().any()}
        if present:
            sheet_sets.append(present)
    if len(sheet_sets) <= 1:
        return 0.0

    union = set().union(*sheet_sets)
    intersection = set.intersection(*sheet_sets)
    return 1 - len(intersection) / max(len(union), 1)


def analyze_sampling_integrity(df: pd.DataFrame, profile: DataProfile) -> dict:
    reasons: list[str] = []
    metrics: dict[str, float | int | str | None] = {
        "time_column": profile.time_column,
        "duplicate_timestamp_ratio": 0.0,
        "interval_cv": 0.0,
        "break_count": 0,
        "estimated_missing_slots": 0,
        "longest_missing_run": 0,
        "sheet_structure_mismatch": 0.0,
        "skipped_sheet_count": len(profile.skipped_sheets or []),
    }

    penalty = 0.0
    if not profile.time_column:
        penalty += 18
        reasons.append("未识别到时间列，无法复核采样间隔、重复时间戳和连续缺测。")
    else:
        times = pd.to_datetime(df[profile.time_column], errors="coerce").dropna().sort_values()
        valid_count = len(times)
        if valid_count < 4:
            penalty += 14
            reasons.append("可解析时间点过少，采样完整性只能作为弱提示。")
        else:
            duplicate_ratio = float(times.duplicated().mean())
            deltas = times.drop_duplicates().diff().dropna().dt.total_seconds()
            positive = deltas[deltas > 0]
            interval_cv = 0.0
            break_count = 0
            missing_slots = 0
            longest_missing_run = 0
            if len(positive):
                median_interval = float(positive.median())
                mean_interval = float(positive.mean())
                interval_cv = float(positive.std(ddof=0) / mean_interval) if mean_interval else 0.0
                if median_interval > 0:
                    gap_slots = np.maximum(np.floor(positive.to_numpy() / median_interval).astype(int) - 1, 0)
                    break_count = int((positive > median_interval * 3).sum())
                    missing_slots = int(gap_slots.sum())
                    longest_missing_run = int(gap_slots.max()) if len(gap_slots) else 0

            metrics.update(
                {
                    "valid_timestamp_count": valid_count,
                    "duplicate_timestamp_ratio": round(duplicate_ratio, 4),
                    "interval_cv": round(interval_cv, 4),
                    "break_count": break_count,
                    "estimated_missing_slots": missing_slots,
                    "longest_missing_run": longest_missing_run,
                }
            )
            duplicate_penalty = ramp_up_penalty(duplicate_ratio, 0.01, 0.10, 22)
            interval_penalty = ramp_up_penalty(interval_cv, 0.35, 1.20, 22)
            break_penalty = min(18.0, break_count * 4.0)
            missing_penalty = ramp_up_penalty(longest_missing_run, 2, 12, 14)
            penalty += duplicate_penalty + interval_penalty + break_penalty + missing_penalty
            metrics.update(
                {
                    "duplicate_penalty": round(duplicate_penalty, 4),
                    "interval_penalty": round(interval_penalty, 4),
                    "break_penalty": round(break_penalty, 4),
                    "missing_run_penalty": round(missing_penalty, 4),
                }
            )
            if duplicate_penalty > 0:
                reasons.append("存在重复时间戳，可能是重复上传、合并错误或设备重复记录。")
            if interval_penalty > 0:
                reasons.append("采样时间间隔波动较大，需要复核采集频率是否稳定。")
            if break_penalty > 0:
                reasons.append("发现明显采样断点，可能存在连续缺测或设备离线。")
            if missing_penalty > 0:
                reasons.append("估计存在较长连续缺测区间，建议查看原始采集日志。")

    mismatch = _sheet_structure_mismatch(df)
    skipped = len(profile.skipped_sheets or [])
    mismatch_penalty = ramp_up_penalty(mismatch, 0.20, 0.80, 14)
    skipped_penalty = min(8.0, skipped * 3.0)
    penalty += mismatch_penalty + skipped_penalty
    metrics.update(
        {
            "sheet_structure_mismatch": round(mismatch, 4),
            "sheet_structure_penalty": round(mismatch_penalty, 4),
            "skipped_sheet_penalty": round(skipped_penalty, 4),
        }
    )
    if mismatch_penalty > 0:
        reasons.append("多个 sheet 的字段结构差异较大，合并后缺失和列含义需要人工确认。")
    if skipped_penalty > 0:
        reasons.append("Excel 中存在空 sheet，系统已跳过，但建议确认是否漏填。")
    if not reasons:
        reasons.append("采样时间和文件结构未发现明显完整性风险。")

    return {
        "score": clamp_score(100 - penalty),
        "risk": "ok" if penalty < 30 else "attention",
        "reasons": reasons,
        "metrics": metrics,
        "charts": [],
    }
