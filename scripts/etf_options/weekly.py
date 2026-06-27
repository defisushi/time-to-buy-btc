"""Weekly table construction and archive upsert logic."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import ETF_TICKERS, WEEK, WEEKLY_CSV
from .utils import upsert_csv


def _week_end(series: pd.Series, week: str = WEEK) -> pd.Series:
    return pd.to_datetime(series, utc=True).dt.tz_convert(None).dt.to_period(week).dt.end_time.dt.normalize()


def _build_flow_weekly(flows: pd.DataFrame, week_end: str) -> pd.DataFrame:
    if flows.empty:
        return pd.DataFrame()
    data = flows.copy()
    data["week_end"] = _week_end(data["event_date"], week_end)
    data["net_flow_usd_m"] = pd.to_numeric(data["net_flow_usd_m"], errors="coerce")
    pivot = data.groupby(["week_end", "ticker"])["net_flow_usd_m"].sum(min_count=1).unstack()
    result = pd.DataFrame(index=pivot.index)
    total = pivot["TOTAL"] if "TOTAL" in pivot else pivot[[c for c in pivot.columns if c in ETF_TICKERS]].sum(axis=1, min_count=1)
    result["etf_net_1w"] = total
    for ticker in ETF_TICKERS:
        result[f"etf_net_{ticker.lower()}"] = pivot[ticker] if ticker in pivot else np.nan

    total_daily = data[data["ticker"] == "TOTAL"].copy()
    result["etf_days_pos"] = total_daily.groupby("week_end")["net_flow_usd_m"].apply(lambda s: int((s > 0).sum()))
    result["avail_date_etf"] = data.groupby("week_end")["avail_date"].max()
    result["etf_cum"] = result["etf_net_1w"].fillna(0).cumsum()
    result["etf_mom_4w"] = result["etf_net_1w"].rolling(4, min_periods=1).mean()
    return result


def _build_price_weekly(price_daily: pd.DataFrame, week_end: str) -> pd.DataFrame:
    if price_daily.empty:
        return pd.DataFrame()
    data = price_daily.copy()
    data["week_end"] = _week_end(data["date"], week_end)
    result = data.groupby("week_end").agg(
        btc_close=("close", "last"),
        btc_vol_1w=("log_return", lambda s: float(s.std() * np.sqrt(52)) if s.notna().sum() > 1 else np.nan),
        btc_volume_1w=("volume", "sum"),
    )
    result["btc_ret_1w"] = result["btc_close"].pct_change()
    return result


def _build_options_weekly(options_daily: pd.DataFrame, week_end: str) -> pd.DataFrame:
    if options_daily.empty:
        return pd.DataFrame()
    data = options_daily.copy()
    data["week_end"] = _week_end(data["date"], week_end)
    metric_cols = [
        "opt_oi_total",
        "opt_pcr_oi",
        "opt_pcr_vol",
        "opt_gex_net",
        "opt_gamma_flip",
        "opt_skew_25d_30d",
        "opt_maxpain_front",
        "opt_dvol",
        "opt_term_slope",
    ]
    present = [col for col in metric_cols if col in data.columns]
    if not present:
        return pd.DataFrame()
    return data.groupby("week_end")[present].last()


def build_weekly(flows: pd.DataFrame, options_daily: pd.DataFrame, price_daily: pd.DataFrame, week_end: str = WEEK) -> pd.DataFrame:
    """Build weekly rows with sum-vs-last aggregation rules from PLAN.md."""
    parts = [_build_price_weekly(price_daily, week_end), _build_flow_weekly(flows, week_end), _build_options_weekly(options_daily, week_end)]
    non_empty = [part for part in parts if not part.empty]
    if not non_empty:
        return pd.DataFrame()
    weekly = pd.concat(non_empty, axis=1).sort_index()

    option_cols = [col for col in weekly.columns if col.startswith("opt_")]
    quality_flags = pd.Series("", index=weekly.index, dtype=object)
    if option_cols:
        missing_before = weekly[option_cols].isna().any(axis=1)
        weekly[option_cols] = weekly[option_cols].ffill()
        quality_flags.loc[missing_before & weekly[option_cols].notna().any(axis=1)] = "options_ffill"

    weekly["quality_flags"] = quality_flags
    weekly = weekly.reset_index()
    weekly["week_end"] = pd.to_datetime(weekly["week_end"], utc=True).dt.date.astype(str)
    if "avail_date_etf" in weekly:
        weekly["avail_date_etf"] = pd.to_datetime(weekly["avail_date_etf"], utc=True).dt.date.astype(str)
    return weekly


def upsert_weekly_csv(df: pd.DataFrame, path: str | Path = WEEKLY_CSV) -> pd.DataFrame:
    """Append/update weekly rows by week_end so Git history becomes the database."""
    return upsert_csv(df, Path(path), key="week_end")
