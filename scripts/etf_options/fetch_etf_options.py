#!/usr/bin/env python3
"""Fetch and compute the ETF flows x options positioning page payload."""

from __future__ import annotations

import logging
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    __package__ = "etf_options"

from .analysis import correlations, granger, lead_lag, rule_based_regime, weekly_conviction
from .backtest import walk_forward
from .config import ETF_TICKERS, OPTIONS_SNAPSHOT_JSON, PUBLIC_JSON, WEEK, WEEKLY_CSV
from .options_metrics import summarize_snapshot
from .serialize import build_payload
from .sources_etf import fetch_etf_flows, load_etf_flows_from_file
from .sources_options import load_snapshot, save_snapshot, snapshot_options, fetch_dvol, fetch_index_price
from .sources_price import get_price_history
from .utils import atomic_write_json, read_weekly_csv
from .weekly import build_weekly, upsert_weekly_csv

LOG = logging.getLogger("etf_options")


def _empty_flows() -> pd.DataFrame:
    return pd.DataFrame(columns=["event_date", "ticker", "net_flow_usd_m", "avail_date", "source"])


def _empty_price() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "log_return", "realized_vol_7d"])


def _fallback_weekly() -> pd.DataFrame:
    existing = read_weekly_csv(WEEKLY_CSV)
    if not existing.empty:
        return existing
    today = pd.Timestamp(datetime.now(timezone.utc)).to_period(WEEK).end_time.normalize()
    row = {
        "week_end": today.date().isoformat(),
        "btc_close": None,
        "btc_ret_1w": None,
        "btc_vol_1w": None,
        "btc_volume_1w": None,
        "etf_net_1w": None,
        "etf_cum": None,
        "etf_mom_4w": None,
        "etf_days_pos": None,
        "avail_date_etf": (today + pd.offsets.BusinessDay(1)).date().isoformat(),
        "quality_flags": "bootstrap_placeholder",
    }
    for ticker in ETF_TICKERS:
        row[f"etf_net_{ticker.lower()}"] = None
    return pd.DataFrame([row])


def _fetch_live_inputs(flows_file: str | Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float | None]:
    start = "2024-01-01"
    end = datetime.now(timezone.utc)

    try:
        if flows_file:
            LOG.info("Loading Farside ETF flow history from manual file: %s", flows_file)
            flows = load_etf_flows_from_file(flows_file)
        else:
            LOG.info("Fetching Farside ETF flow history")
            flows = fetch_etf_flows()
    except Exception as exc:
        LOG.warning("ETF flow fetch failed: %s", exc)
        flows = _empty_flows()

    try:
        LOG.info("Fetching BTC price history")
        price = get_price_history(start, end)
    except Exception as exc:
        LOG.warning("BTC price fetch failed: %s", exc)
        price = _empty_price()

    dvol: float | None = None
    try:
        LOG.info("Fetching Deribit option chain")
        chain = snapshot_options("BTC")
        spot = fetch_index_price()
        dvol = fetch_dvol()
        if not chain.empty:
            chain["underlying_price"] = chain["underlying_price"].fillna(spot)
            save_snapshot(chain, OPTIONS_SNAPSHOT_JSON)
    except Exception as exc:
        LOG.warning("Deribit option fetch failed: %s", exc)
        chain = load_snapshot(OPTIONS_SNAPSHOT_JSON)

    return flows, price, chain, dvol


def run(flows_file: str | Path | None = None) -> dict:
    """Run the full idempotent weekly pipeline and return the JSON payload."""
    existing_weekly = read_weekly_csv(WEEKLY_CSV)
    flows, price, chain, dvol = _fetch_live_inputs(flows_file=flows_file)
    option_summary = summarize_snapshot(chain, float(chain["underlying_price"].dropna().median()), dvol) if not chain.empty else {}
    options_daily = pd.DataFrame([option_summary]) if option_summary else pd.DataFrame()

    weekly_new = build_weekly(flows, options_daily, price, week_end=WEEK)
    if weekly_new.empty:
        weekly = _fallback_weekly()
    else:
        if flows.empty and not existing_weekly.empty:
            preserve = [col for col in existing_weekly.columns if col.startswith("etf_") or col == "avail_date_etf"]
            weekly_new = weekly_new[weekly_new["week_end"].isin(existing_weekly["week_end"])]
            weekly_new = weekly_new.drop(columns=[col for col in preserve if col in weekly_new.columns], errors="ignore")
            weekly_new = weekly_new.merge(existing_weekly[["week_end", *preserve]], on="week_end", how="left")
        weekly = upsert_weekly_csv(weekly_new, WEEKLY_CSV)

    signals = weekly_conviction(weekly)
    metric_cols = ["etf_net_1w", "etf_mom_4w", "opt_pcr_oi", "opt_gex_net", "opt_skew_25d_30d", "opt_dvol"]
    analysis_outputs = {
        "correlations": correlations(weekly, metrics=metric_cols),
        "leadLag": lead_lag(weekly, metrics=metric_cols),
        "regimes": rule_based_regime(weekly),
        "granger": granger(weekly, "btc_ret_1w", metric_cols),
    }
    bt = walk_forward(signals, "conviction")
    payload = build_payload(weekly, chain, analysis_outputs, signals, bt)
    atomic_write_json(PUBLIC_JSON, payload)
    if not chain.empty:
        save_snapshot(chain, OPTIONS_SNAPSHOT_JSON)
    LOG.info("Wrote %s with %d weekly rows", PUBLIC_JSON, len(payload.get("weekly", [])))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch ETF flows/options data and write the public payload.")
    parser.add_argument("--flows-file", default=os.environ.get("FARSIDE_FLOWS_FILE"), help="Manual Farside HTML/CSV/XLSX export to use instead of the network scrape.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(flows_file=args.flows_file)


if __name__ == "__main__":
    main()
