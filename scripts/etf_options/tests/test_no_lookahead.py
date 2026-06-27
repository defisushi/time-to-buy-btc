from __future__ import annotations

import numpy as np
import pandas as pd

from etf_options.analysis import _expanding_zscore, weekly_conviction


def _weekly_frame(rows: int = 16) -> pd.DataFrame:
    dates = pd.date_range("2026-01-02", periods=rows, freq="W-FRI")
    return pd.DataFrame(
        {
            "week_end": dates.date.astype(str),
            "btc_close": np.linspace(50000, 65000, rows),
            "btc_ret_1w": np.linspace(-0.03, 0.04, rows),
            "etf_mom_4w": np.linspace(-400, 500, rows),
            "etf_net_1w": np.linspace(-800, 900, rows),
            "opt_skew_25d_30d": np.linspace(-5, 4, rows),
            "opt_pcr_oi": np.linspace(1.4, 0.6, rows),
            "opt_gamma_flip": np.linspace(51000, 64000, rows),
        }
    )


def test_conviction_is_causal():
    weekly = _weekly_frame(18)
    first_n = 12

    partial = weekly_conviction(weekly.iloc[:first_n])
    full = weekly_conviction(weekly)

    np.testing.assert_allclose(partial["conviction"], full["conviction"].iloc[:first_n], atol=1e-9)


def test_zscore_expanding_uses_only_past():
    values = pd.Series(range(1, 11), dtype=float)

    actual = _expanding_zscore(values, min_periods=3)

    expected = []
    for idx, value in values.items():
        window = values.iloc[: idx + 1]
        if len(window) < 3:
            expected.append(0.0)
        else:
            expected.append((value - window.mean()) / window.std())
    np.testing.assert_allclose(actual, expected, atol=1e-12)

