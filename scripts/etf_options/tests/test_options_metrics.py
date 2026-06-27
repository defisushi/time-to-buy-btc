from __future__ import annotations

import pandas as pd
import pytest

from etf_options.options_metrics import compute_gex, compute_max_pain, compute_pcr, compute_skew


def _chain() -> pd.DataFrame:
    snapshot = pd.Timestamp("2026-06-01T00:00:00Z")
    expiry = pd.Timestamp("2026-07-01T00:00:00Z")
    return pd.DataFrame(
        [
            {"snapshot_ts": snapshot, "expiry": expiry, "strike": 90, "type": "P", "oi": 10, "volume_24h": 4, "mark_iv": 50, "delta": -0.25, "gamma": 0.01, "underlying_price": 100},
            {"snapshot_ts": snapshot, "expiry": expiry, "strike": 100, "type": "P", "oi": 20, "volume_24h": 6, "mark_iv": 55, "delta": -0.50, "gamma": 0.01, "underlying_price": 100},
            {"snapshot_ts": snapshot, "expiry": expiry, "strike": 100, "type": "C", "oi": 20, "volume_24h": 5, "mark_iv": 55, "delta": 0.50, "gamma": 0.01, "underlying_price": 100},
            {"snapshot_ts": snapshot, "expiry": expiry, "strike": 110, "type": "C", "oi": 10, "volume_24h": 5, "mark_iv": 50, "delta": 0.25, "gamma": 0.01, "underlying_price": 100},
        ]
    )


def test_compute_skew_symmetric_chain_is_zero():
    assert abs(compute_skew(_chain(), tenor_days=30)) < 1e-6


def test_max_pain_equilibrium_strike():
    chain = _chain()
    assert compute_max_pain(chain, chain["expiry"].iloc[0]) == 100


def test_gamma_flip_near_spot_for_balanced_oi():
    result = compute_gex(_chain(), spot=100)
    assert abs(result["gamma_flip_level"] - 100) <= 10


def test_gamma_flip_ignores_deep_otm_noise_crossing():
    snapshot = pd.Timestamp("2026-06-01T00:00:00Z")
    expiry = pd.Timestamp("2026-07-01T00:00:00Z")
    chain = pd.DataFrame(
        [
            {"snapshot_ts": snapshot, "expiry": expiry, "strike": 40, "type": "C", "oi": 1, "volume_24h": 0, "mark_iv": 50, "delta": 0.01, "gamma": 0.01, "underlying_price": 100},
            {"snapshot_ts": snapshot, "expiry": expiry, "strike": 50, "type": "P", "oi": 2, "volume_24h": 0, "mark_iv": 50, "delta": -0.01, "gamma": 0.01, "underlying_price": 100},
            {"snapshot_ts": snapshot, "expiry": expiry, "strike": 90, "type": "P", "oi": 20, "volume_24h": 0, "mark_iv": 50, "delta": -0.35, "gamma": 0.01, "underlying_price": 100},
            {"snapshot_ts": snapshot, "expiry": expiry, "strike": 100, "type": "C", "oi": 50, "volume_24h": 0, "mark_iv": 50, "delta": 0.50, "gamma": 0.01, "underlying_price": 100},
            {"snapshot_ts": snapshot, "expiry": expiry, "strike": 110, "type": "C", "oi": 5, "volume_24h": 0, "mark_iv": 50, "delta": 0.25, "gamma": 0.01, "underlying_price": 100},
        ]
    )

    result = compute_gex(chain, spot=100)

    assert result["gamma_flip_level"] == 100


def test_compute_pcr_known_counts():
    result = compute_pcr(_chain())
    assert result["pcr_oi"] == pytest.approx(30 / 30)
    assert result["pcr_vol"] == pytest.approx(10 / 10)
