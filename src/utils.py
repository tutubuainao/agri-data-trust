from __future__ import annotations

import os
from pathlib import Path
import re
from uuid import uuid4

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path.cwd() / ".cache"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = [
    "PingFang SC",
    "Heiti SC",
    "Songti SC",
    "Arial Unicode MS",
    "Noto Sans CJK SC",
    "SimHei",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False
import numpy as np
import pandas as pd


def clamp_score(value: float) -> float:
    return float(max(0.0, min(100.0, value)))


def clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").dropna().astype(float)


def safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def safe_filename_part(value: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", str(value), flags=re.UNICODE).strip("._")
    return text[:80] or "chart"


def save_line_plot(series: pd.Series, title: str, reports_dir: Path, prefix: str) -> str | None:
    values = clean_numeric(series)
    if len(values) < 2:
        return None
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{safe_filename_part(prefix)}_{uuid4().hex[:8]}.png"
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(np.arange(len(values)), values.to_numpy(), linewidth=1.6)
    ax.set_title(title)
    ax.set_xlabel("Observation")
    ax.set_ylabel(series.name or "value")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return str(path)


def save_bar_plot(labels: list[str], values: list[float], title: str, reports_dir: Path, prefix: str) -> str | None:
    if not labels:
        return None
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{safe_filename_part(prefix)}_{uuid4().hex[:8]}.png"
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylim(0, max(values + [1]) * 1.15)
    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return str(path)
