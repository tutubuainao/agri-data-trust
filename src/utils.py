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
from matplotlib import font_manager

import numpy as np
import pandas as pd


def configure_chinese_font() -> None:
    """Configure matplotlib with a CJK-capable font when the system has one."""
    candidates = [
        "PingFang SC",
        "Hiragino Sans GB",
        "Heiti SC",
        "STHeiti",
        "Songti SC",
        "Noto Sans CJK SC",
        "Noto Sans CJK",
        "Source Han Sans SC",
        "WenQuanYi Zen Hei",
        "SimHei",
        "Microsoft YaHei",
        "Arial Unicode MS",
    ]
    known_names = {font.name for font in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in known_names:
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            break
    else:
        common_paths = [
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/arphic/SimHei.ttf",
        ]
        for path in common_paths:
            if Path(path).exists():
                font_manager.fontManager.addfont(path)
                prop = font_manager.FontProperties(fname=path)
                plt.rcParams["font.sans-serif"] = [prop.get_name(), "DejaVu Sans"]
                break
    plt.rcParams["axes.unicode_minus"] = False


configure_chinese_font()


def clamp_score(value: float) -> float:
    return float(max(0.0, min(100.0, value)))


def ramp_up_penalty(value: float, start: float, full: float, max_penalty: float) -> float:
    """Penalty grows from 0 at start to max_penalty at full as value increases."""
    if full == start:
        return max_penalty if value > start else 0.0
    ratio = (value - start) / (full - start)
    return max_penalty * max(0.0, min(1.0, ratio))


def ramp_down_penalty(value: float, start: float, full: float, max_penalty: float) -> float:
    """Penalty grows from 0 at start to max_penalty at full as value decreases."""
    if full == start:
        return max_penalty if value < start else 0.0
    ratio = (start - value) / (start - full)
    return max_penalty * max(0.0, min(1.0, ratio))


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
    ax.set_xlabel("样本序号")
    ax.set_ylabel(series.name or "数值")
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
