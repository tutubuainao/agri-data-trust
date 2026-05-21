from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def load_data(file: str | Path | BinaryIO, filename: str | None = None) -> pd.DataFrame:
    """Load CSV or Excel data into a DataFrame."""
    suffix = Path(filename or str(file)).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only CSV, XLSX, and XLS files are supported.")

    if suffix == ".csv":
        return pd.read_csv(file)
    return pd.read_excel(file)
