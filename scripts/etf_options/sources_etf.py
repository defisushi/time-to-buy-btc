"""Farside BTC ETF flow scraper."""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from .config import ETF_TICKERS
from .utils import retry

FARSIDE_URL = "https://farside.co.uk/btc/"


def clean_flow(value: object) -> float | None:
    """Parse Farside currency cells such as '(123.4)', '-', '$1,234.5'."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().replace("$", "").replace(",", "")
    if text in {"", "-", "–", "—", "nan"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text:
        return None
    parsed = float(text)
    return -abs(parsed) if negative else parsed


def _normalise_columns(columns: list[object]) -> list[str]:
    names: list[str] = []
    for column in columns:
        if isinstance(column, tuple):
            column = " ".join(str(part) for part in column if "Unnamed" not in str(part))
        name = re.sub(r"\s+", " ", str(column)).strip()
        upper = name.upper()
        if upper in ETF_TICKERS:
            names.append(upper)
        elif "TOTAL" in upper:
            names.append("TOTAL")
        elif "DATE" in upper:
            names.append("DATE")
        else:
            names.append(upper)
    return names


def _pick_flow_table(html: str | io.StringIO) -> pd.DataFrame:
    source = io.StringIO(html) if isinstance(html, str) else html
    tables = pd.read_html(source)
    for table in tables:
        table.columns = _normalise_columns(list(table.columns))
        columns = set(table.columns)
        if "DATE" in columns and "TOTAL" in columns and len(columns.intersection(ETF_TICKERS)) >= 3:
            return table
    raise RuntimeError("Could not find expected Farside BTC ETF flow table")


def _flows_from_table(table: pd.DataFrame, source: str = "Farside Investors") -> pd.DataFrame:
    """Convert a Farside-like wide table into normalized long-form ETF flows."""
    table = table.copy()
    table.columns = _normalise_columns(list(table.columns))
    columns = set(table.columns)
    ticker_columns = [col for col in ETF_TICKERS if col in columns]
    if "DATE" not in columns or "TOTAL" not in columns or len(ticker_columns) < 1:
        raise RuntimeError("Farside table is missing DATE, Total, or ETF ticker columns")

    table["event_date"] = pd.to_datetime(table["DATE"], errors="coerce", utc=True)
    table = table.dropna(subset=["event_date"])

    value_columns = ticker_columns + ["TOTAL"]
    rows: list[dict[str, object]] = []
    for _, row in table.iterrows():
        event_date = pd.Timestamp(row["event_date"]).normalize()
        avail_date = event_date + pd.offsets.BusinessDay(1)
        for col in value_columns:
            rows.append(
                {
                    "event_date": event_date,
                    "ticker": "TOTAL" if col == "TOTAL" else col,
                    "net_flow_usd_m": clean_flow(row[col]),
                    "avail_date": avail_date,
                    "source": source,
                }
            )

    frame = pd.DataFrame(rows)
    return frame.sort_values(["event_date", "ticker"]).reset_index(drop=True)


def load_etf_flows_from_file(path: str | Path) -> pd.DataFrame:
    """Load manually downloaded Farside ETF flows from HTML, CSV, or XLSX."""
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix in {".html", ".htm"}:
        table = _pick_flow_table(io.StringIO(file_path.read_text(encoding="utf-8")))
    elif suffix == ".csv":
        table = pd.read_csv(file_path)
        table.columns = _normalise_columns(list(table.columns))
    elif suffix in {".xlsx", ".xls"}:
        table = pd.read_excel(file_path)
        table.columns = _normalise_columns(list(table.columns))
    else:
        raise RuntimeError(f"Unsupported Farside flows file type: {file_path.suffix}")
    return _flows_from_table(table, source="Farside Investors (manual)")


def fetch_etf_flows(lookback_days: int | None = None) -> pd.DataFrame:
    """Fetch long-form daily BTC ETF flows in USD millions from Farside."""
    def call() -> str:
        resp = requests.get(
            FARSIDE_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text

    flows = _flows_from_table(_pick_flow_table(retry(call)))
    if lookback_days is not None:
        cutoff = pd.Timestamp(datetime.now(timezone.utc)) - pd.Timedelta(days=lookback_days)
        flows = flows[flows["event_date"] >= cutoff]
    return flows.reset_index(drop=True)


def fetch_recent_revisions(days: int = 5) -> pd.DataFrame:
    """Re-scrape a trailing window to capture Farside revisions."""
    return fetch_etf_flows(lookback_days=days)
