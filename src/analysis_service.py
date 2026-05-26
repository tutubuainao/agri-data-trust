from __future__ import annotations

import math
from io import BytesIO
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

import numpy as np
import pandas as pd

from .loader import load_data
from .profiler import profile_data
from .indicator_config import available_indicator_payload, resolve_indicator_selection
from .report import generate_html_report, generate_pdf_report
from .rule_config import scenario_info
from .scoring import run_full_analysis, risk_level
from .screening import ColumnScreening, screen_columns


def _json_safe(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat() if pd.notna(value) else None
    if isinstance(value, (np.ndarray,)):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if pd.isna(value):
        return None
    return value


def _chart_urls(charts: list[str], base_path: str = "/agri-trust") -> list[str]:
    return [f"{base_path}/reports/{Path(chart).name}" for chart in charts]


def _profile_payload(profile) -> dict[str, Any]:
    return {
        "time_column": profile.time_column,
        "numeric_columns": profile.numeric_columns,
        "rows": profile.rows,
        "columns": profile.columns,
        "missing_rate": round(profile.missing_rate, 4),
        "sheet_names": profile.sheet_names or [],
        "used_sheets": profile.used_sheets or [],
        "skipped_sheets": profile.skipped_sheets or [],
    }


def stats_path(reports_dir: Path) -> Path:
    return reports_dir / "usage_stats.json"


def stats_db_path(reports_dir: Path) -> Path:
    configured = os.getenv("USAGE_DB_PATH")
    if configured:
        return Path(configured)
    return reports_dir / "usage_stats.sqlite"


def _empty_usage_stats() -> dict[str, Any]:
    return {
        "files_analyzed": 0,
        "rows_analyzed": 0,
        "numeric_columns_analyzed": 0,
        "sheets_analyzed": 0,
        "last_source": "",
    }


def _legacy_usage_stats(reports_dir: Path) -> dict[str, Any]:
    path = stats_path(reports_dir)
    if not path.exists():
        return _empty_usage_stats()
    try:
        return {**_empty_usage_stats(), **json.loads(path.read_text(encoding="utf-8"))}
    except json.JSONDecodeError:
        return _empty_usage_stats()


def _connect_usage_db(reports_dir: Path) -> sqlite3.Connection:
    path = stats_db_path(reports_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_stats (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            files_analyzed INTEGER NOT NULL DEFAULT 0,
            rows_analyzed INTEGER NOT NULL DEFAULT 0,
            numeric_columns_analyzed INTEGER NOT NULL DEFAULT 0,
            sheets_analyzed INTEGER NOT NULL DEFAULT 0,
            last_source TEXT NOT NULL DEFAULT ''
        )
        """
    )
    row = conn.execute("SELECT COUNT(*) FROM usage_stats WHERE id = 1").fetchone()
    if row[0] == 0:
        legacy = _legacy_usage_stats(reports_dir)
        conn.execute(
            """
            INSERT INTO usage_stats (
                id, files_analyzed, rows_analyzed, numeric_columns_analyzed,
                sheets_analyzed, last_source
            ) VALUES (1, ?, ?, ?, ?, ?)
            """,
            (
                int(legacy.get("files_analyzed", 0)),
                int(legacy.get("rows_analyzed", 0)),
                int(legacy.get("numeric_columns_analyzed", 0)),
                int(legacy.get("sheets_analyzed", 0)),
                str(legacy.get("last_source", "")),
            ),
        )
        conn.commit()
    return conn


def load_usage_stats(reports_dir: Path) -> dict[str, Any]:
    with _connect_usage_db(reports_dir) as conn:
        row = conn.execute(
            """
            SELECT files_analyzed, rows_analyzed, numeric_columns_analyzed,
                   sheets_analyzed, last_source
            FROM usage_stats WHERE id = 1
            """
        ).fetchone()
    if row is None:
        return _empty_usage_stats()
    return {
        "files_analyzed": int(row[0]),
        "rows_analyzed": int(row[1]),
        "numeric_columns_analyzed": int(row[2]),
        "sheets_analyzed": int(row[3]),
        "last_source": row[4] or "",
    }


def record_usage(reports_dir: Path, source_name: str, profile_payload: dict[str, Any]) -> dict[str, Any]:
    used_sheets = profile_payload.get("used_sheets") or []
    with _connect_usage_db(reports_dir) as conn:
        conn.execute(
            """
            UPDATE usage_stats
            SET files_analyzed = files_analyzed + 1,
                rows_analyzed = rows_analyzed + ?,
                numeric_columns_analyzed = numeric_columns_analyzed + ?,
                sheets_analyzed = sheets_analyzed + ?,
                last_source = ?
            WHERE id = 1
            """,
            (
                int(profile_payload.get("rows", 0)),
                len(profile_payload.get("numeric_columns", [])),
                max(len(used_sheets), 1),
                source_name,
            ),
        )
        conn.commit()
    return load_usage_stats(reports_dir)


def _screening_payload(records: list[ColumnScreening]) -> list[dict[str, Any]]:
    return [
        {
            "column": item.column,
            "raw_dtype": item.raw_dtype,
            "role": item.role,
            "entered_analysis": item.entered_analysis,
            "non_null_count": item.non_null_count,
            "missing_rate": round(item.missing_rate, 4),
            "unique_count": item.unique_count,
            "numeric_valid_rate": round(item.numeric_valid_rate, 4),
            "datetime_valid_rate": round(item.datetime_valid_rate, 4),
            "handling": item.handling,
        }
        for item in records
    ]


def _analysis_payload(analysis: dict[str, Any], base_path: str = "/agri-trust") -> dict[str, Any]:
    column_results: dict[str, dict[str, Any]] = {}
    for col, checks in analysis["column_results"].items():
        column_results[col] = {}
        for key, result in checks.items():
            column_results[col][key] = {
                "label": result.get("label", key),
                "score": round(float(result.get("score", 0)), 2),
                "risk": result.get("risk"),
                "reasons": result.get("reasons", []),
                "metrics": _json_safe(result.get("metrics", {})),
                "charts": _chart_urls(result.get("charts", []), base_path),
            }

    correlation = analysis["correlation"]
    pearson = correlation.get("pearson")
    spearman = correlation.get("spearman")
    dataset_results: dict[str, dict[str, Any]] = {}
    for key, result in analysis.get("dataset_results", {}).items():
        dataset_results[key] = {
            "label": result.get("label", key),
            "score": round(float(result.get("score", 0)), 2),
            "risk": result.get("risk"),
            "reasons": result.get("reasons", []),
            "metrics": _json_safe(result.get("metrics", {})),
            "charts": _chart_urls(result.get("charts", []), base_path),
        }

    return {
        "total_score": round(float(analysis["total_score"]), 2),
        "risk_level": analysis["risk_level"],
        "weights": {
            key: round(float(value), 4)
            for key, value in analysis.get("weights", {}).items()
        },
        "sub_scores": {
            key: {
                "score": round(float(value), 2),
                "risk_level": risk_level(float(value)),
            }
            for key, value in analysis["sub_scores"].items()
        },
        "reasons": analysis["reasons"],
        "dataset_results": dataset_results,
        "column_results": column_results,
        "selected_indicators": analysis.get("selected_indicators", []),
        "available_indicators": analysis.get("available_indicators", available_indicator_payload()),
        "indicator_selection_mode": analysis.get("indicator_selection_mode", "默认核心指标"),
        "indicator_selection": analysis.get("indicator_selection", {}),
        "correlation": {
            "label": correlation.get("label", "多变量相关性检测"),
            "score": round(float(correlation.get("score")), 2) if correlation.get("score") is not None else None,
            "risk": correlation.get("risk"),
            "reasons": correlation.get("reasons", []),
            "metrics": _json_safe(correlation.get("metrics", {})),
            "charts": _chart_urls(correlation.get("charts", []), base_path),
            "pearson": _json_safe(pearson.round(4).to_dict()) if hasattr(pearson, "round") else {},
            "spearman": _json_safe(spearman.round(4).to_dict()) if hasattr(spearman, "round") else {},
            "skipped": bool(correlation.get("skipped", False)),
        },
    }


def analyze_dataframe(
    df: pd.DataFrame,
    source_name: str,
    reports_dir: Path,
    base_path: str = "/agri-trust",
    record_stats: bool = False,
    scenario: str | None = "auto",
    indicators: list[str] | str | None = None,
    custom_indicators: bool = False,
) -> dict[str, Any]:
    prepared, profile = profile_data(df)
    screening_records = screen_columns(df, profile)
    profile_payload = _profile_payload(profile)
    scenario_payload = scenario_info(scenario)
    selection_payload = resolve_indicator_selection(
        scenario_payload["key"],
        indicators,
        custom_indicators,
    )

    if not profile.numeric_columns:
        if record_stats:
            record_usage(reports_dir, source_name, profile_payload)
        return {
            "ok": False,
            "message": "未识别到可分析的数值列。请检查文件是否包含至少一个可解析率 >= 70%、有效唯一值数 >= 3 的数值列。",
            "source_name": source_name,
            "profile": profile_payload,
            "scenario": scenario_payload,
            "indicator_selection": selection_payload,
            "available_indicators": selection_payload["available"],
            "selected_indicators": selection_payload["selected"],
            "screening": _screening_payload(screening_records),
            "preview": _json_safe(prepared.head(30).to_dict(orient="records")),
            "stats": load_usage_stats(reports_dir),
        }

    analysis = run_full_analysis(
        prepared,
        profile,
        reports_dir,
        scenario_payload["key"],
        indicators=indicators,
        custom_indicators=custom_indicators,
    )
    html_path = generate_html_report(
        analysis,
        profile,
        source_name,
        reports_dir,
        screening_records=screening_records,
        scenario=scenario_payload,
    )
    pdf_path = generate_pdf_report(
        analysis,
        profile,
        source_name,
        reports_dir,
        screening_records=screening_records,
        scenario=scenario_payload,
    )
    stats = record_usage(reports_dir, source_name, profile_payload) if record_stats else load_usage_stats(reports_dir)

    return {
        "ok": True,
        "source_name": source_name,
        "profile": profile_payload,
        "scenario": scenario_payload,
        "screening": _screening_payload(screening_records),
        "preview": _json_safe(prepared.head(30).to_dict(orient="records")),
        "analysis": _analysis_payload(analysis, base_path),
        "report_url": f"{base_path}/reports/{html_path.name}",
        "pdf_report_url": f"{base_path}/reports/{pdf_path.name}",
        "stats": stats,
    }


def analyze_file_bytes(
    content: bytes,
    filename: str,
    reports_dir: Path,
    base_path: str = "/agri-trust",
    record_stats: bool = False,
    scenario: str | None = "auto",
    indicators: list[str] | str | None = None,
    custom_indicators: bool = False,
) -> dict[str, Any]:
    df = load_data(BytesIO(content), filename)
    return analyze_dataframe(
        df,
        filename,
        reports_dir,
        base_path,
        record_stats=record_stats,
        scenario=scenario,
        indicators=indicators,
        custom_indicators=custom_indicators,
    )
