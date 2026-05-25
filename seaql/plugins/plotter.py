from __future__ import annotations

import shutil
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


def _format_x_value(val: Any, compact: bool = False) -> str:
    dt = _parse_date(str(val))
    if dt is not None:
        if compact:
            if dt.hour == 0 and dt.minute == 0:
                return dt.strftime("%m-%d")
            return dt.strftime("%H:%M")
        return dt.strftime("%m-%d %H:%M")
    s = str(val)
    return s[:8] if len(s) > 8 else s


def _chart_offset(chart: str) -> int:
    lines = chart.split("\n")
    for line in lines:
        for i, ch in enumerate(line):
            if ch in ("┼", "┤", "╰", "╭", "╮", "╯", "│", "╴", "╶", "─"):
                return i
    return 10


def _render_x_axis(chart: str, x_values: list) -> str:
    n = len(x_values)
    if n <= 1:
        return chart

    offset = _chart_offset(chart)
    width = offset + n

    all_dates = all(_parse_date(str(v)) is not None for v in x_values)
    multi_day = False
    if all_dates:
        dates = [_parse_date(str(v)) for v in x_values]
        first_date = dates[0].date()
        multi_day = any(d.date() != first_date for d in dates)

    if all_dates and not multi_day:
        label_w = 5
        max_ticks = max(2, (n - 1) // (label_w + 1))
        step = max(1, (n - 1) // (max_ticks - 1))
        indices = list(range(0, n, step))
        if indices[-1] != n - 1:
            indices.append(n - 1)

        labels = [dates[i].strftime("%H:%M") for i in indices]
        cols = [offset + i for i in indices]

        tick_row = [" "] * width
        for c in cols:
            if c < width:
                tick_row[c] = "|"

        label_row = _place_labels(width, offset, cols, labels)
        return chart + "\n" + "".join(tick_row) + "\n" + "".join(label_row)

    if all_dates and multi_day:
        label_w = 5
        max_ticks = max(2, (n - 1) // (label_w + 1))
        step = max(1, (n - 1) // (max_ticks - 1))
        indices = list(range(0, n, step))
        if indices[-1] != n - 1:
            indices.append(n - 1)

        time_labels = [dates[i].strftime("%H:%M") for i in indices]
        date_labels = []
        prev_date = None
        for i in indices:
            d = dates[i].date()
            date_labels.append(d.strftime("%m-%d") if d != prev_date else "")
            prev_date = d

        cols = [offset + i for i in indices]

        tick_row = [" "] * width
        for c in cols:
            if c < width:
                tick_row[c] = "|"

        date_row = _place_labels(width, offset, cols, date_labels)
        time_row = _place_labels(width, offset, cols, time_labels)
        return chart + "\n" + "".join(tick_row) + "\n" + "".join(date_row) + "\n" + "".join(time_row)

    sample = str(x_values[0])[:8]
    label_w = len(sample)
    max_ticks = max(2, (n - 1) // (label_w + 1))
    step = max(1, (n - 1) // (max_ticks - 1))
    indices = list(range(0, n, step))
    if indices[-1] != n - 1:
        indices.append(n - 1)

    labels = [(str(x_values[i])[:8]) for i in indices]
    cols = [offset + i for i in indices]

    tick_row = [" "] * width
    for c in cols:
        if c < width:
            tick_row[c] = "|"

    label_row = _place_labels(width, offset, cols, labels)
    return chart + "\n" + "".join(tick_row) + "\n" + "".join(label_row)


def _place_labels(width: int, offset: int, cols: list[int], labels: list[str]) -> str:
    row = [" "] * width
    prev_end = -1
    for c, label in zip(cols, labels):
        if not label:
            continue
        pos = c - len(label) // 2
        pos = max(offset, pos)
        if pos + len(label) > width:
            pos = width - len(label)
        if pos <= prev_end + 1:
            pos = prev_end + 2
        if pos + len(label) <= width:
            for j, ch in enumerate(label):
                if pos + j < width:
                    row[pos + j] = ch
            prev_end = pos + len(label) - 1
    return "".join(row)


def _downsample(x_vals: list, y_vals: list[float], max_points: int):
    n = len(y_vals)
    if n <= max_points:
        return x_vals, y_vals
    step = (n - 1) / (max_points - 1) if max_points > 1 else 0
    indices = [int(round(i * step)) for i in range(max_points)]
    return [x_vals[i] for i in indices], [y_vals[i] for i in indices]


def _estimate_offset(y_vals: list[float]) -> int:
    lo, hi = min(y_vals), max(y_vals)
    label_w = max(len(f"{lo:.2f}"), len(f"{hi:.2f}")) + 1
    return max(10, label_w + 3)


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
    x_vals: list[Any] = []

    for r in rows:
        yv = r[y_idx]
        if yv is None:
            continue
        try:
            yf = float(yv)
        except (ValueError, TypeError):
            continue
        y_vals.append(yf)
        x_vals.append(r[x_idx] if x_idx is not None else len(y_vals))

    if not y_vals:
        return [(None, None, None, "No valid numeric data to plot.")]

    term_w = shutil.get_terminal_size().columns
    est_offset = _estimate_offset(y_vals)
    max_pts = max(10, term_w - est_offset)
    x_vals, y_vals = _downsample(x_vals, y_vals, max_pts)

    chart = plot(y_vals, {"height": 12})
    chart = _render_x_axis(chart, x_vals)

    print(f"  y: {y_label}  |  x: {x_label if x_idx is not None else 'row'}")
    print("")
    print(chart)

    return [(None, None, None, "")]
