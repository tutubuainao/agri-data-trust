from __future__ import annotations

from pathlib import Path
from typing import BinaryIO
import re
import warnings

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
SHEET_COLUMN = "__sheet__"


def _clean_label(value: object) -> str:
    if pd.isna(value):
        return ""
    text = re.sub(r"\s+", "", str(value).strip())
    if text.lower().startswith("unnamed:"):
        return ""
    return text


def _looks_like_extra_header(row: pd.Series) -> bool:
    non_empty = [_clean_label(value) for value in row.tolist()]
    non_empty = [value for value in non_empty if value]
    if len(non_empty) < 3:
        return False
    numeric_rate = pd.to_numeric(row, errors="coerce").notna().mean()
    return numeric_rate < 0.25


def _unique_columns(columns: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    out: list[str] = []
    for idx, col in enumerate(columns, start=1):
        base = col or f"未命名列{idx}"
        counts[base] = counts.get(base, 0) + 1
        out.append(base if counts[base] == 1 else f"{base}_{counts[base]}")
    return out


def _parse_sheet(raw: pd.DataFrame, sheet_name: str) -> pd.DataFrame | None:
    raw = raw.dropna(axis=0, how="all").dropna(axis=1, how="all")
    if raw.empty:
        return None

    first = raw.iloc[0].tolist()
    header_rows = 1
    if len(raw) > 1 and _looks_like_extra_header(raw.iloc[1]):
        header_rows = 2

    if header_rows == 2:
        top = pd.Series(first).ffill().tolist()
        second = raw.iloc[1].tolist()
        columns = []
        for upper, lower in zip(top, second):
            upper_label = _clean_label(upper)
            lower_label = _clean_label(lower)
            if upper_label and lower_label and upper_label != lower_label:
                columns.append(f"{upper_label}-{lower_label}")
            else:
                columns.append(lower_label or upper_label)
    else:
        columns = [_clean_label(item) for item in first]

    data = raw.iloc[header_rows:].copy()
    data.columns = _unique_columns(columns)
    data = data.dropna(axis=0, how="all").dropna(axis=1, how="all")
    if data.empty:
        return None
    data.insert(0, SHEET_COLUMN, sheet_name)
    return data.reset_index(drop=True)


def _load_excel(file: str | Path | BinaryIO) -> pd.DataFrame:
    try:
        excel = pd.ExcelFile(file)
    except ImportError as exc:
        if "xlrd" in str(exc).lower():
            raise ValueError("读取 .xls 文件需要安装 xlrd 依赖，请先执行 pip install xlrd，或另存为 .xlsx 后上传。") from exc
        raise

    frames: list[pd.DataFrame] = []
    skipped: list[str] = []
    for sheet_name in excel.sheet_names:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            raw = excel.parse(sheet_name, header=None)
        parsed = _parse_sheet(raw, str(sheet_name))
        if parsed is None:
            skipped.append(str(sheet_name))
            continue
        frames.append(parsed)

    if not frames:
        skipped_text = "、".join(skipped) if skipped else "全部 sheet"
        raise ValueError(f"Excel 中未发现可分析数据，已跳过空 sheet：{skipped_text}。")

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined.attrs["sheet_names"] = excel.sheet_names
    combined.attrs["used_sheets"] = [str(frame[SHEET_COLUMN].iloc[0]) for frame in frames]
    combined.attrs["skipped_sheets"] = skipped
    return combined


def load_data(file: str | Path | BinaryIO, filename: str | None = None) -> pd.DataFrame:
    """Load CSV or Excel data into a DataFrame."""
    suffix = Path(filename or str(file)).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only CSV, XLSX, and XLS files are supported.")

    if suffix == ".csv":
        return pd.read_csv(file)
    return _load_excel(file)
