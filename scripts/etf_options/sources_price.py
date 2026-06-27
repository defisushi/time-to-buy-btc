"""BTC price history fetchers using public, keyless endpoints."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import requests

from .utils import retry

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
COINGECKO_MARKET_CHART = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range"


def _to_ms(value: date | datetime | str) -> int:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return int(ts.timestamp() * 1000)


def _binance_chunk(start_ms: int, end_ms: int) -> list[list[Any]]:
    def call() -> list[list[Any]]:
        resp = requests.get(
            BINANCE_KLINES,
            params={"symbol": "BTCUSDT", "interval": "1d", "startTime": start_ms, "endTime": end_ms, "limit": 1000},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    return retry(call)


def _from_binance(start: date | datetime | str, end: date | datetime | str) -> pd.DataFrame:
    start_ms = _to_ms(start)
    end_ms = _to_ms(end)
    rows: list[list[Any]] = []
    cursor = start_ms
    one_day_ms = 86_400_000
    while cursor <= end_ms:
        chunk = _binance_chunk(cursor, end_ms)
        if not chunk:
            break
        rows.extend(chunk)
        cursor = int(chunk[-1][0]) + one_day_ms
        if len(chunk) < 1000:
            break

    if not rows:
        raise RuntimeError("Binance returned no BTCUSDT klines")

    frame = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_base",
            "taker_quote",
            "ignore",
        ],
    )
    frame["date"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True).dt.normalize()
    for col in ["open", "high", "low", "close", "volume"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame[["date", "open", "high", "low", "close", "volume"]].drop_duplicates("date")


def _from_coingecko(start: date | datetime | str, end: date | datetime | str) -> pd.DataFrame:
    start_s = _to_ms(start) // 1000
    end_s = _to_ms(end) // 1000

    def call() -> dict[str, Any]:
        resp = requests.get(
            COINGECKO_MARKET_CHART,
            params={"vs_currency": "usd", "from": start_s, "to": end_s},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    data = retry(call)
    prices = pd.DataFrame(data.get("prices", []), columns=["ts", "close"])
    volumes = pd.DataFrame(data.get("total_volumes", []), columns=["ts", "volume"])
    if prices.empty:
        raise RuntimeError("CoinGecko returned no BTC price history")
    frame = prices.merge(volumes, on="ts", how="left")
    frame["date"] = pd.to_datetime(frame["ts"], unit="ms", utc=True).dt.normalize()
    daily = frame.groupby("date", as_index=False).agg(close=("close", "last"), volume=("volume", "sum"))
    daily["open"] = daily["close"]
    daily["high"] = daily["close"]
    daily["low"] = daily["close"]
    return daily[["date", "open", "high", "low", "close", "volume"]]


def get_price_history(start: date | datetime | str, end: date | datetime | str | None = None) -> pd.DataFrame:
    """Return daily BTC OHLCV with log returns and 7-day realized volatility."""
    end = end or datetime.now(timezone.utc)
    try:
        frame = _from_binance(start, end)
    except Exception:
        frame = _from_coingecko(start, end)

    frame = frame.sort_values("date").reset_index(drop=True)
    frame["log_return"] = np.log(frame["close"] / frame["close"].shift(1))
    frame["realized_vol_7d"] = frame["log_return"].rolling(7).std() * np.sqrt(365)
    return frame
