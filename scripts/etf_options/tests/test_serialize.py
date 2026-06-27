from __future__ import annotations

import json

import pandas as pd

from etf_options.serialize import build_payload


def test_build_payload_schema_json_safe():
    weekly = pd.DataFrame(
        [
            {
                "week_end": "2026-06-26",
                "btc_close": 60000.0,
                "etf_net_1w": 100.0,
                "opt_gex_net": 1.0,
                "opt_skew_25d_30d": 0.5,
            }
        ]
    )
    chain = pd.DataFrame(
        [
            {"snapshot_ts": pd.Timestamp("2026-06-26T00:00:00Z"), "expiry": pd.Timestamp("2026-07-01T00:00:00Z"), "strike": 60000.0, "type": "C", "oi": 10, "volume_24h": 1, "gamma": 0.00002, "underlying_price": 60000.0},
            {"snapshot_ts": pd.Timestamp("2026-06-26T00:00:00Z"), "expiry": pd.Timestamp("2026-07-01T00:00:00Z"), "strike": 59000.0, "type": "P", "oi": 10, "volume_24h": 1, "gamma": 0.00002, "underlying_price": 60000.0},
        ]
    )
    signals = weekly.assign(
        conviction=10.0,
        flow_confirmation=True,
        bearish_divergence=False,
        capitulation_contrarian=False,
        gamma_regime="above_flip",
    )
    payload = build_payload(
        weekly,
        chain,
        {"leadLag": [], "correlations": [], "regimes": [{"week_end": "2026-06-26", "label": "Bull-Calm"}]},
        signals,
        {"equity": [], "sharpe": None, "max_dd": None, "hit_rate": None, "turnover": None, "vs_hodl": None},
    )

    assert {"lastUpdated", "weekly", "latestSnapshot", "leadLag", "correlations", "regimes", "signals", "backtest"} <= set(payload)
    assert {"spot", "gamma_flip", "gexByStrike", "maxPainByExpiry"} <= set(payload["latestSnapshot"])
    json.dumps(payload)

