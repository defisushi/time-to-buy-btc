"""Build the compact JSON payload consumed by the React ETF/options page."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .options_metrics import compute_gex, max_pain_by_expiry
from .utils import records


def _round_value(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: _round_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_round_value(item) for item in value]
    return value


def _latest_snapshot(chain: pd.DataFrame) -> dict[str, Any]:
    if chain.empty:
        return {"spot": None, "gamma_flip": None, "gexByStrike": [], "maxPainByExpiry": []}
    spot = chain["underlying_price"].dropna().median()
    if pd.isna(spot):
        spot = None
    gex = compute_gex(chain, float(spot)) if spot else {"gex_by_strike": [], "gamma_flip_level": None}
    return {
        "spot": float(spot) if spot else None,
        "gamma_flip": gex["gamma_flip_level"],
        "gexByStrike": gex["gex_by_strike"],
        "maxPainByExpiry": max_pain_by_expiry(chain),
    }


def build_payload(
    weekly: pd.DataFrame,
    latest_snapshot: pd.DataFrame,
    analysis_outputs: dict[str, Any],
    signals: pd.DataFrame,
    backtest: dict[str, Any],
) -> dict[str, Any]:
    """Build the documented ETF/options JSON schema."""
    weekly_data = weekly.copy()
    if "week_end" in weekly_data:
        weekly_data["week_end"] = pd.to_datetime(weekly_data["week_end"], utc=True).dt.date.astype(str)
    signal_cols = [
        "week_end",
        "conviction",
        "flow_confirmation",
        "bearish_divergence",
        "capitulation_contrarian",
        "gamma_regime",
    ]
    present_signal_cols = [col for col in signal_cols if col in signals.columns]
    latest_signal = signals.iloc[-1] if not signals.empty else {}
    payload = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "weekly": records(weekly_data),
        "latestSnapshot": _latest_snapshot(latest_snapshot),
        "leadLag": analysis_outputs.get("leadLag", []),
        "correlations": analysis_outputs.get("correlations", []),
        "regimes": analysis_outputs.get("regimes", []),
        "signals": {
            "conviction": float(latest_signal.get("conviction", 0)) if len(signals) else 0,
            "flags": {
                "flow_confirmation": bool(latest_signal.get("flow_confirmation", False)) if len(signals) else False,
                "bearish_divergence": bool(latest_signal.get("bearish_divergence", False)) if len(signals) else False,
                "capitulation_contrarian": bool(latest_signal.get("capitulation_contrarian", False)) if len(signals) else False,
                "gamma_regime": latest_signal.get("gamma_regime", "unknown") if len(signals) else "unknown",
            },
            "history": records(signals[present_signal_cols]) if present_signal_cols else [],
        },
        "backtest": backtest,
    }
    return _round_value(payload)

