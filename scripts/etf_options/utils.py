"""Shared helpers for retrying, CSV upserts, and atomic JSON writes."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Iterable, TypeVar

import pandas as pd

T = TypeVar("T")


def retry(fn: Callable[[], T], attempts: int = 3, base_sleep: float = 1.0) -> T:
    """Run a callable with simple exponential backoff."""
    last_error: Exception | None = None
    for idx in range(attempts):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - exercised by live network failures
            last_error = exc
            if idx < attempts - 1:
                time.sleep(base_sleep * (2**idx))
    assert last_error is not None
    raise last_error


def clean_for_json(value: Any) -> Any:
    """Convert pandas/numpy scalars, NaN, and timestamps into JSON-safe values."""
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp,)):
        if pd.isna(value):
            return None
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {str(k): clean_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_for_json(v) for v in value]
    return value


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON via rename so readers never see a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_payload = clean_for_json(payload)
    with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
        json.dump(safe_payload, tmp, indent=2, sort_keys=False)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def read_weekly_csv(path: Path) -> pd.DataFrame:
    """Read the weekly archive if it exists, otherwise return an empty frame."""
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    if "week_end" in frame.columns:
        frame["week_end"] = pd.to_datetime(frame["week_end"], utc=True).dt.date.astype(str)
    return frame


def upsert_csv(rows: pd.DataFrame, path: Path, key: str = "week_end") -> pd.DataFrame:
    """Append/update rows in a CSV archive by key and return the full sorted archive.

    Existing non-null cells are preserved when an incoming row has nulls. This matters for
    option metrics because a weekly run can revise ETF/price fields for older rows without
    having historical option-chain snapshots to refill those same rows.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_weekly_csv(path)
    incoming = rows.copy()
    if key not in incoming.columns:
        incoming = incoming.reset_index()
    incoming[key] = pd.to_datetime(incoming[key], utc=True).dt.date.astype(str)

    if existing.empty:
        combined = incoming.sort_values(key)
    else:
        column_order = list(existing.columns) + [col for col in incoming.columns if col not in existing.columns]
        incoming_indexed = incoming.set_index(key)
        existing_indexed = existing.set_index(key)
        combined = incoming_indexed.combine_first(existing_indexed).reset_index()
        combined = combined.reindex(columns=[col for col in column_order if col in combined.columns])
        combined = combined.sort_values(key)
    combined.to_csv(path, index=False)
    return combined


def records(frame: pd.DataFrame, columns: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Return compact JSON records with timestamps and NaN values cleaned."""
    use = frame.loc[:, list(columns)] if columns else frame
    return clean_for_json(use.to_dict(orient="records"))
