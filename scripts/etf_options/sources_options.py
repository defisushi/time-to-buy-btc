"""Deribit public options snapshot client."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from .config import DERIBIT_BASE, OPTIONS_SNAPSHOT_JSON
from .utils import atomic_write_json, retry

INSTRUMENT_RE = re.compile(r"^(?P<currency>[A-Z]+)-(?P<expiry>\d{1,2}[A-Z]{3}\d{2})-(?P<strike>\d+(?:\.\d+)?)-(?P<type>[CP])$")
LOG = logging.getLogger(__name__)


def _get(method: str, params: dict[str, Any] | None = None) -> Any:
    def call() -> Any:
        resp = requests.get(f"{DERIBIT_BASE}/public/{method}", params=params or {}, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        if "error" in payload:
            raise RuntimeError(payload["error"])
        return payload.get("result")

    return retry(call)


def parse_instrument(name: str) -> dict[str, Any]:
    """Parse Deribit option names such as BTC-27JUN25-60000-C."""
    match = INSTRUMENT_RE.match(name)
    if not match:
        raise ValueError(f"Unrecognised Deribit option instrument: {name}")
    expiry = datetime.strptime(match.group("expiry"), "%d%b%y").replace(tzinfo=timezone.utc)
    return {
        "instrument": name,
        "expiry": pd.Timestamp(expiry),
        "strike": float(match.group("strike")),
        "type": match.group("type"),
    }


def _ticker(instrument_name: str) -> dict[str, Any]:
    result = _get("ticker", {"instrument_name": instrument_name})
    return result if isinstance(result, dict) else {}


def snapshot_options(currency: str = "BTC", ticker_limit: int = 200) -> pd.DataFrame:
    """Fetch a point-in-time BTC option chain.

    Historical free Deribit option chains are not recoverable after the fact, so the weekly
    archive begins when this project first runs and stores derived metrics going forward.
    """
    summaries = _get("get_book_summary_by_currency", {"currency": currency, "kind": "option"})
    instruments = _get("get_instruments", {"currency": currency, "kind": "option", "expired": "false"})
    instrument_meta = {item["instrument_name"]: item for item in instruments}
    snapshot_ts = pd.Timestamp(datetime.now(timezone.utc))
    rows: list[dict[str, Any]] = []

    sorted_summaries = sorted(summaries, key=lambda row: float(row.get("open_interest") or 0), reverse=True)
    for idx, item in enumerate(sorted_summaries):
        name = item.get("instrument_name")
        if not name:
            continue
        try:
            parsed = parse_instrument(name)
        except ValueError as exc:
            LOG.warning("Skipping malformed Deribit option instrument %s: %s", name, exc)
            continue
        meta = instrument_meta.get(name, {})
        ticker_data: dict[str, Any] = {}
        greeks = item.get("greeks") or {}
        if idx < ticker_limit and (not greeks or item.get("mark_iv") is None):
            try:
                ticker_data = _ticker(name)
                greeks = ticker_data.get("greeks") or greeks
            except Exception:
                ticker_data = {}
        rows.append(
            {
                "snapshot_ts": snapshot_ts,
                **parsed,
                "oi": float(item.get("open_interest") or 0),
                "volume_24h": float(item.get("volume") or item.get("volume_usd") or 0),
                "mark_iv": item.get("mark_iv") or ticker_data.get("mark_iv"),
                "delta": greeks.get("delta"),
                "gamma": greeks.get("gamma"),
                "vega": greeks.get("vega"),
                "mark_price": item.get("mark_price") or ticker_data.get("mark_price"),
                "underlying_price": item.get("underlying_price") or ticker_data.get("underlying_price") or item.get("estimated_delivery_price"),
                "expiration_timestamp": meta.get("expiration_timestamp"),
            }
        )

    frame = pd.DataFrame(rows)
    numeric_cols = ["strike", "oi", "volume_24h", "mark_iv", "delta", "gamma", "vega", "mark_price", "underlying_price"]
    for col in numeric_cols:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame.sort_values(["expiry", "strike", "type"]).reset_index(drop=True)


def fetch_dvol(currency: str = "BTC") -> float | None:
    """Fetch the latest Deribit volatility index value."""
    end = int(datetime.now(timezone.utc).timestamp() * 1000)
    start = end - 3 * 24 * 60 * 60 * 1000
    result = _get("get_volatility_index_data", {"currency": currency, "start_timestamp": start, "end_timestamp": end, "resolution": "1D"})
    rows = result.get("data", []) if isinstance(result, dict) else result
    if not rows:
        return None
    last = rows[-1]
    if isinstance(last, list):
        return float(last[4] if len(last) >= 5 else last[-1])
    return float(last.get("close", last.get("value")))


def fetch_index_price(index_name: str = "btc_usd") -> float:
    """Fetch the latest Deribit BTC index price."""
    result = _get("get_index_price", {"index_name": index_name})
    return float(result["index_price"])


def save_snapshot(df: pd.DataFrame, path: Path = OPTIONS_SNAPSHOT_JSON) -> None:
    """Overwrite the latest full option-chain snapshot for frontend strike charts."""
    atomic_write_json(path, {"rows": df.to_dict(orient="records")})


def load_snapshot(path: Path = OPTIONS_SNAPSHOT_JSON) -> pd.DataFrame:
    """Load the saved latest option-chain snapshot."""
    if not path.exists():
        return pd.DataFrame()
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    frame = pd.DataFrame(data.get("rows", []))
    for col in ["snapshot_ts", "expiry"]:
        if col in frame.columns:
            frame[col] = pd.to_datetime(frame[col], utc=True, errors="coerce")
    return frame
