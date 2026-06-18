"""CSV loading.

Reads a CSV with pandas, identifies the Time column (the X axis), and builds one
:class:`Series` per remaining numeric column. Non-numeric columns are skipped.
Problems are raised as :class:`CsvLoadError` for the UI to report.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.api import types as pdt

from .series import Series, palette_color


class CsvLoadError(Exception):
    """Raised when a CSV cannot be loaded or has no usable data."""


@dataclass
class LoadedCsv:
    path: Path
    time_name: str          # the column used as the X axis
    series: list[Series]    # one per plottable data column


def _pick_time_column(df: pd.DataFrame) -> str:
    """Return the column to use as Time: a column literally named 'time'
    (case-insensitive) if present, otherwise the first column."""
    for col in df.columns:
        if str(col).strip().lower() == "time":
            return col
    return df.columns[0]


def load_csv(path: str | Path) -> LoadedCsv:
    path = Path(path)
    try:
        df = pd.read_csv(path)
    except FileNotFoundError as exc:
        raise CsvLoadError(f"File not found:\n{path}") from exc
    except pd.errors.EmptyDataError as exc:
        raise CsvLoadError("The file is empty.") from exc
    except Exception as exc:  # parse errors, encoding issues, etc.
        raise CsvLoadError(f"Could not parse the CSV:\n{exc}") from exc

    if df.shape[1] < 2:
        raise CsvLoadError(
            "Need at least two columns: a Time column and one or more data columns."
        )

    time_name = _pick_time_column(df)

    time_values = pd.to_numeric(df[time_name], errors="coerce")
    if time_values.isna().all():
        raise CsvLoadError(
            f"The Time column ('{time_name}') has no numeric values."
        )
    x = time_values.to_numpy(dtype=float)

    series: list[Series] = []
    for col in df.columns:
        if col == time_name:
            continue
        if not pdt.is_numeric_dtype(df[col]):
            continue  # skip text/label columns
        y = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        series.append(
            Series(name=str(col), x=x, y=y, color=palette_color(len(series)))
        )

    if not series:
        raise CsvLoadError("No numeric data columns found to plot.")

    return LoadedCsv(path=path, time_name=str(time_name), series=series)
