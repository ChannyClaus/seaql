from __future__ import annotations

from datetime import datetime
from typing import Any

from asciichartpy import plot

_last_headers: list[str] | None = None
_last_rows: list[tuple] | None = None


def store_result(headers: Any, rows: Any) -> None:
    global _last_headers, _last_rows
    if headers is not None and rows is not None:
        _last_headers = list(headers)
        _last_rows = [tuple(r) for r in rows]


def _find_column(headers: list[str], name: str) -> int | None:
    for i, h in enumerate(headers):
        if h.lower() == name.lower():
            return i
    for i, h in enumerate(headers):
        if name.lower() in h.lower():
            return i
    return None


_DATE_FMTS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%H:%M:%S")


def _parse_date(val: Any) -> datetime | None:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in _DATE_FMTS:
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
    return None


def _auto_detect_columns(headers, rows):
    numeric = []
    dates = []
    for i, h in enumerate(headers):
        vals = [r[i] for r in rows if r[i] is not None]
        if not vals:
            continue
        nums = []
        for v in vals:
            try:
                nums.append(float(v))
            except (ValueError, TypeError):
                nums = None
                break
        if nums is not None:
            numeric.append((i, h))
            continue
        if any(_parse_date(str(v)) is not None for v in vals[:5]):
            dates.append((i, h))
    return numeric, dates


def plot_timeseries(arg: str = "") -> list[tuple]:
    global _last_headers, _last_rows

    if not _last_headers or not _last_rows:
        return [(None, None, None, "No data to plot. Run a SELECT query first.")]

    headers = _last_headers
    rows = _last_rows
    parts = arg.split() if arg.strip() else []
    numeric, dates = _auto_detect_columns(headers, rows)

    if not numeric:
        return [(None, None, None, "No numeric columns found in results.")]

    if len(parts) == 0:
        if dates and numeric:
            x_idx, x_label = dates[0]
            y_idx, y_label = numeric[0]
        else:
            x_idx, x_label = None, "row"
            y_idx, y_label = numeric[0]
    elif len(parts) == 1:
        y_idx = _find_column(headers, parts[0])
        if y_idx is None:
            return [(None, None, None, f"Column '{parts[0]}' not found.")]
        y_label = headers[y_idx]
        if dates:
            x_idx, x_label = dates[0]
        else:
            x_idx, x_label = None, "row"
    else:
        x_idx = _find_column(headers, parts[0])
        y_idx = _find_column(headers, parts[1])
        if x_idx is None:
            return [(None, None, None, f"Column '{parts[0]}' not found.")]
        if y_idx is None:
            return [(None, None, None, f"Column '{parts[1]}' not found.")]
        x_label, y_label = parts[0], parts[1]

    y_vals: list[float] = []

    for r in rows:
        yv = r[y_idx]
        if yv is None:
            continue
        try:
            yf = float(yv)
        except (ValueError, TypeError):
            continue
        y_vals.append(yf)

    if not y_vals:
        return [(None, None, None, "No valid numeric data to plot.")]

    chart = plot(y_vals, {"height": 12})
    print(f"  y: {y_label}")
    if x_idx is not None and x_label:
        print(f"  x: {x_label}")
    print("")
    print(chart)

    return [(None, None, None, "")]
