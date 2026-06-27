from __future__ import annotations

import pandas as pd
import pytest

from etf_options.backtest import walk_forward


def _weekly_frame() -> pd.DataFrame:
    dates = pd.date_range("2026-01-02", periods=10, freq="W-FRI")
    returns = [0.00, 0.02, -0.01, 0.03, -0.02, 0.04, -0.01, 0.03, -0.02, 0.04]
    return pd.DataFrame(
        {
            "week_end": dates.date.astype(str),
            "avail_date_etf": (dates + pd.offsets.BusinessDay(1)).date.astype(str),
            "btc_ret_1w": returns,
        }
    )


def test_lookahead_assertion_fires():
    weekly = _weekly_frame()
    weekly["signal"] = [1, -1, 1, -1, 1, -1, 1, -1, 1, -1]
    weekly["signal_source_week_end"] = weekly["week_end"].shift(-1)

    with pytest.raises(AssertionError):
        walk_forward(weekly, "signal")


def test_perfect_foresight_beats_hodl():
    weekly = _weekly_frame()
    weekly["signal"] = 0
    for idx in range(len(weekly) - 2):
        weekly.loc[idx, "signal"] = 1 if weekly.loc[idx + 2, "btc_ret_1w"] > 0 else -1

    result = walk_forward(weekly, "signal", cost_bps=0)

    assert result["equity"][-1]["strategy"] > result["equity"][-1]["hodl"]


def test_costs_reduce_returns():
    weekly = _weekly_frame()
    weekly["signal"] = 1

    free = walk_forward(weekly, "signal", cost_bps=0)
    costly = walk_forward(weekly, "signal", cost_bps=50)

    assert free["equity"][-1]["strategy"] > costly["equity"][-1]["strategy"]

