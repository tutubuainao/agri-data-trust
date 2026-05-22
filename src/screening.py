from __future__ import annotations

from dataclasses import dataclass
import warnings

import pandas as pd

from .profiler import DataProfile
from .profiler import is_identifier_column


@dataclass
class ColumnScreening:
    column: str
    raw_dtype: str
    role: str
    entered_analysis: bool
    non_null_count: int
    missing_rate: float
    unique_count: int
    numeric_valid_rate: float
    datetime_valid_rate: float
    handling: str


def screen_columns(df: pd.DataFrame, profile: DataProfile) -> list[ColumnScreening]:
    records: list[ColumnScreening] = []
    numeric_set = set(profile.numeric_columns)
    min_valid_count = min(max(8, int(len(df) * 0.08)), 30)

    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        non_null_count = int(non_null.shape[0])
        missing_rate = 1 - non_null_count / max(len(series), 1)
        unique_count = int(non_null.nunique(dropna=True))
        numeric_valid_rate = float(pd.to_numeric(series, errors="coerce").notna().mean())
        numeric_valid_count = int(pd.to_numeric(series, errors="coerce").notna().sum())

        name_hint = any(
            key in str(col).lower()
            for key in ["time", "date", "timestamp", "datetime", "采集", "日期", "时间"]
        )
        numeric_like = numeric_valid_rate >= 0.8
        parsed_dates = pd.Series(dtype="datetime64[ns]")
        if numeric_like and not name_hint:
            datetime_valid_rate = 0.0
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                parsed_dates = pd.to_datetime(series, errors="coerce")
            datetime_valid_rate = float(parsed_dates.notna().mean())
        valid_dates = parsed_dates.dropna() if "parsed_dates" in locals() else pd.Series(dtype="datetime64[ns]")
        plausible_year_rate = (
            float(((valid_dates.dt.year >= 1990) & (valid_dates.dt.year <= 2100)).mean())
            if len(valid_dates)
            else 0.0
        )
        date_like = datetime_valid_rate >= 0.6 and plausible_year_rate >= 0.8 and (name_hint or not numeric_like)

        if non_null_count == 0:
            role = "空列"
            entered = False
            handling = "整列为空，不进入可信度指标计算；在数据概况中体现为缺失。"
        elif is_identifier_column(col):
            role = "编号/代码列"
            entered = False
            handling = "该列看起来是序号、编号或行政区代码，用于标识记录，不代表农业采集指标；已排除出可信度评分。"
        elif col == profile.time_column:
            role = "时间列"
            entered = False
            handling = "用于排序和时间序列解释，不作为数值变量评分。无法解析的时间值会转为缺失并排在后面。"
        elif col in numeric_set:
            role = "数值检测列"
            entered = True
            handling = "进入五类可信度检测；缺失值不填补，在各指标计算前按需剔除。"
        elif numeric_valid_rate >= 0.7 and numeric_valid_count < min_valid_count:
            role = "有效样本不足"
            entered = False
            handling = f"该列虽然可转为数值，但有效数值只有 {numeric_valid_count} 个，低于当前最小样本要求 {min_valid_count} 个；为避免少量值误导评分，已剔除并在粗筛表反馈。"
        elif numeric_valid_rate >= 0.7 and unique_count < 3:
            role = "数值但变化不足"
            entered = False
            handling = "可转为数值，但有效唯一值少于 3 个，可能是常量列、停滞传感器或填充值；不进入时间序列类检测。"
        elif date_like:
            role = "日期/时间辅助列"
            entered = False
            handling = "可解析为日期时间，但不是主时间列；当前版本仅保留一个时间列用于排序，其余日期列不评分。"
        elif numeric_valid_rate < 0.7:
            role = "文本/分类列"
            entered = False
            handling = "非数值内容占比较高，当前 MVP 不对文本或分类变量做可信度评分。"
        else:
            role = "未纳入检测"
            entered = False
            handling = "未满足数值列准入条件，暂不进入五类指标计算。"

        if entered and missing_rate > 0.3:
            handling += " 注意：该列缺失率超过 30%，有效样本会减少，结论需要谨慎解释。"

        records.append(
            ColumnScreening(
                column=str(col),
                raw_dtype=str(series.dtype),
                role=role,
                entered_analysis=entered,
                non_null_count=non_null_count,
                missing_rate=float(missing_rate),
                unique_count=unique_count,
                numeric_valid_rate=numeric_valid_rate,
                datetime_valid_rate=datetime_valid_rate,
                handling=handling,
            )
        )

    return records


def screening_dataframe(records: list[ColumnScreening]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "列名": item.column,
                "原始类型": item.raw_dtype,
                "粗筛角色": item.role,
                "进入检测": "是" if item.entered_analysis else "否",
                "非空数": item.non_null_count,
                "缺失率": f"{item.missing_rate:.2%}",
                "唯一值数": item.unique_count,
                "数值可解析率": f"{item.numeric_valid_rate:.2%}",
                "时间可解析率": f"{item.datetime_valid_rate:.2%}",
                "处理方式": item.handling,
            }
            for item in records
        ]
    )
