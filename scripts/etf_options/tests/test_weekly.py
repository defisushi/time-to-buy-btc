from __future__ import annotations

import pandas as pd
import pytest

from etf_options.weekly import build_weekly


def test_weekly_aggregation_rules_and_availability():
    flows = pd.DataFrame(
        [
            {"event_date": "2026-01-05", "ticker": "TOTAL", "net_flow_usd_m": 100, "avail_date": "2026-01-06"},
            {"event_date": "2026-01-06", "ticker": "TOTAL", "net_flow_usd_m": -20, "avail_date": "2026-01-07"},
            {"event_date": "2026-01-05", "ticker": "IBIT", "net_flow_usd_m": 70, "avail_date": "2026-01-06"},
            {"event_date": "2026-01-06", "ticker": "IBIT", "net_flow_usd_m": 10, "avail_date": "2026-01-07"},
            {"event_date": "2026-01-05", "ticker": "FBTC", "net_flow_usd_m": 30, "avail_date": "2026-01-06"},
        ]
    )
    price = pd.DataFrame(
        [
            {"date": "2026-01-02", "close": 100, "volume": 1, "log_return": 0.01},
            {"date": "2026-01-05", "close": 101, "volume": 2, "log_return": 0.01},
            {"date": "2026-01-09", "close": 110, "volume": 3, "log_return": 0.02},
        ]
    )
    options = pd.DataFrame(
        [
            {"date": "2026-01-06", "opt_gex_net": 1, "opt_dvol": 40},
            {"date": "2026-01-09", "opt_gex_net": 2, "opt_dvol": 45},
        ]
    )

    weekly = build_weekly(flows, options, price)
    row = weekly[weekly["week_end"] == "2026-01-09"].iloc[0]

    assert row["etf_net_1w"] == 80
    assert row["etf_net_ibit"] == 80
    assert row["etf_days_pos"] == 1
    assert row["opt_gex_net"] == 2
    assert row["btc_close"] == 110
    assert row["btc_ret_1w"] == pytest.approx(0.10)
    assert pd.Timestamp(row["avail_date_etf"]) >= pd.Timestamp("2026-01-06")


def test_flows_not_forward_filled_but_options_are_flagged():
    flows = pd.DataFrame(
        [
            {"event_date": "2026-01-05", "ticker": "TOTAL", "net_flow_usd_m": 100, "avail_date": "2026-01-06"},
        ]
    )
    price = pd.DataFrame(
        [
            {"date": "2026-01-09", "close": 100, "volume": 1, "log_return": 0.01},
            {"date": "2026-01-16", "close": 105, "volume": 1, "log_return": 0.02},
        ]
    )
    options = pd.DataFrame(
        [
            {"date": "2026-01-09", "opt_gex_net": 10, "opt_dvol": 40},
        ]
    )

    weekly = build_weekly(flows, options, price)
    gap = weekly[weekly["week_end"] == "2026-01-16"].iloc[0]

    assert pd.isna(gap["etf_net_1w"])
    assert gap["opt_gex_net"] == 10
    assert gap["quality_flags"] == "options_ffill"
