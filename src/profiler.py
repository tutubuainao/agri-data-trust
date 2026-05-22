from __future__ import annotations

from dataclasses import dataclass
import warnings

import numpy as np
import pandas as pd


ID_COLUMN_HINTS = ["序号", "编号", "代码", "编码", "行政区代码"]


def is_identifier_column(column: object) -> bool:
    name = str(column).strip().lower()
    if any(key in name for key in ID_COLUMN_HINTS):
        return True
    tokens = [token for token in name.replace("-", "_").split("_") if token]
    return name in {"id", "index"} or "id" in tokens or "index" in tokens


@dataclass
class DataProfile:
    time_column: str | None
    numeric_columns: list[str]
    rows: int
    columns: int
    missing_rate: float
    sheet_names: list[str] | None = None
    used_sheets: list[str] | None = None
    skipped_sheets: list[str] | None = None


def detect_time_column(df: pd.DataFrame) -> str | None:
    """Pick the column most likely to represent time."""
    best_col = None
    best_score = 0.0
    min_valid_dates = min(max(8, int(len(df) * 0.05)), 30)

    for col in df.columns:
        series = df[col]
        name_hint = any(key in str(col).lower() for key in ["time", "date", "timestamp", "datetime", "采集", "日期", "时间"])
        numeric_like = pd.to_numeric(series, errors="coerce").notna().mean() >= 0.8
        if numeric_like and not name_hint:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            parsed = pd.to_datetime(series, errors="coerce")
        valid_rate = parsed.notna().mean()
        valid_count = int(parsed.notna().sum())
        years = parsed.dropna().dt.year if valid_count else pd.Series(dtype=int)
        plausible_year_rate = float(((years >= 1990) & (years <= 2100)).mean()) if valid_count else 0.0
        if not name_hint and plausible_year_rate < 0.8:
            continue
        monotonic = parsed.dropna().is_monotonic_increasing
        score = valid_rate + (0.25 if monotonic else 0.0) + (0.2 if name_hint else 0.0)
        if valid_rate >= 0.6 and valid_count >= min_valid_dates and score > best_score:
            best_col = col
            best_score = score

    return best_col


def detect_numeric_columns(df: pd.DataFrame, time_column: str | None = None) -> list[str]:
    numeric_cols: list[str] = []
    min_valid_count = min(max(8, int(len(df) * 0.08)), 30)
    for col in df.columns:
        if col == time_column:
            continue
        if is_identifier_column(col):
            continue
        converted = pd.to_numeric(df[col], errors="coerce")
        valid_rate = converted.notna().mean()
        valid_count = int(converted.notna().sum())
        unique_count = converted.nunique(dropna=True)
        if valid_rate >= 0.7 and valid_count >= min_valid_count and unique_count >= 3:
            numeric_cols.append(col)
    return numeric_cols


def prepare_dataframe(df: pd.DataFrame, time_column: str | None, numeric_columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    if time_column:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            out[time_column] = pd.to_datetime(out[time_column], errors="coerce")
        out = out.sort_values(time_column)
    for col in numeric_columns:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def profile_data(df: pd.DataFrame) -> tuple[pd.DataFrame, DataProfile]:
    time_column = detect_time_column(df)
    numeric_columns = detect_numeric_columns(df, time_column)
    prepared = prepare_dataframe(df, time_column, numeric_columns)
    missing_rate = float(np.mean(prepared.isna().to_numpy())) if prepared.size else 0.0
    return prepared, DataProfile(
        time_column=time_column,
        numeric_columns=numeric_columns,
        rows=len(prepared),
        columns=len(prepared.columns),
        missing_rate=missing_rate,
        sheet_names=df.attrs.get("sheet_names"),
        used_sheets=df.attrs.get("used_sheets"),
        skipped_sheets=df.attrs.get("skipped_sheets"),
    )
