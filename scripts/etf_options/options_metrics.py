"""Pure option-chain metrics used by the weekly BTC ETF/options page."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _cumulative_crossings_by_strike(by_strike: pd.DataFrame, *, ascending: bool) -> list[float]:
    ordered = by_strike.sort_values("strike", ascending=ascending).copy()
    ordered["cum_gex_scan"] = ordered["gex"].cumsum()
    crossings: list[float] = []
    previous = ordered.iloc[0]
    for _, current in ordered.iloc[1:].iterrows():
        prev_cum = float(previous["cum_gex_scan"])
        curr_cum = float(current["cum_gex_scan"])
        if (prev_cum != 0 and curr_cum == 0) or (prev_cum * curr_cum < 0):
            crossings.append(float(current["strike"]))
        previous = current
    return crossings


def compute_pcr(chain: pd.DataFrame) -> dict[str, float | None]:
    """Compute put/call ratios by open interest and 24h volume."""
    calls = chain[chain["type"] == "C"]
    puts = chain[chain["type"] == "P"]
    call_oi = calls["oi"].sum()
    call_vol = calls["volume_24h"].sum()
    return {
        "pcr_oi": float(puts["oi"].sum() / call_oi) if call_oi else None,
        "pcr_vol": float(puts["volume_24h"].sum() / call_vol) if call_vol else None,
    }


def compute_gex(chain: pd.DataFrame, spot: float, multiplier: float = 1.0) -> dict[str, Any]:
    """Compute net gamma exposure by strike.

    Dealer positioning is not observed in public data. This assumes dealers are long gamma
    against calls and short gamma against puts, so calls add positive GEX and puts subtract it.
    Treat the result as a regime/context indicator rather than a precise dealer book.
    """
    usable = chain.dropna(subset=["gamma", "oi", "strike", "type"]).copy()
    sign = np.where(usable["type"] == "C", 1.0, -1.0)
    usable["gex"] = usable["gamma"].astype(float) * usable["oi"].astype(float) * (spot**2) * 0.01 * multiplier * sign
    by_strike = usable.groupby("strike", as_index=False)["gex"].sum().sort_values("strike")
    by_strike["cum_gex"] = by_strike["gex"].cumsum()

    gamma_flip = None
    if not by_strike.empty:
        crossings = [
            *_cumulative_crossings_by_strike(by_strike, ascending=True),
            *_cumulative_crossings_by_strike(by_strike, ascending=False),
        ]
        if crossings:
            gamma_flip = min(crossings, key=lambda strike: abs(strike - spot))
        else:
            fallback = by_strike.assign(
                abs_cum=by_strike["cum_gex"].abs(),
                spot_distance=(by_strike["strike"] - spot).abs(),
            ).sort_values(["abs_cum", "spot_distance"])
            gamma_flip = float(fallback.iloc[0]["strike"])

    return {
        "net_gex": float(by_strike["gex"].sum()) if not by_strike.empty else None,
        "gex_by_strike": by_strike[["strike", "gex"]].to_dict(orient="records"),
        "gamma_flip_level": gamma_flip,
    }


def _nearest_expiry_bucket(chain: pd.DataFrame, tenor_days: int) -> pd.DataFrame:
    now = chain["snapshot_ts"].dropna().max() if "snapshot_ts" in chain.columns else pd.Timestamp.utcnow()
    expiries = chain["expiry"].dropna().drop_duplicates()
    if expiries.empty:
        return pd.DataFrame()
    target = pd.Timestamp(now).tz_convert("UTC") + pd.Timedelta(days=tenor_days)
    expiry = min(expiries, key=lambda value: abs(pd.Timestamp(value) - target))
    return chain[chain["expiry"] == expiry].copy()


def _interpolate_iv(rows: pd.DataFrame, target_delta: float) -> float | None:
    rows = rows.dropna(subset=["delta", "mark_iv"]).sort_values("delta")
    if rows.empty:
        return None
    if len(rows) == 1:
        return float(rows.iloc[0]["mark_iv"])
    return float(np.interp(target_delta, rows["delta"].astype(float), rows["mark_iv"].astype(float)))


def compute_skew(chain: pd.DataFrame, tenor_days: int = 30) -> float | None:
    """Return 25-delta risk reversal: 25d call IV minus 25d put IV."""
    bucket = _nearest_expiry_bucket(chain, tenor_days)
    if bucket.empty:
        return None
    call_iv = _interpolate_iv(bucket[bucket["type"] == "C"], 0.25)
    put_iv = _interpolate_iv(bucket[bucket["type"] == "P"], -0.25)
    if call_iv is None or put_iv is None:
        return None
    return float(call_iv - put_iv)


def compute_max_pain(chain: pd.DataFrame, expiry: object) -> float | None:
    """Find the strike that minimizes option-holder intrinsic payout for an expiry."""
    bucket = chain[chain["expiry"] == expiry].dropna(subset=["strike", "oi", "type"])
    if bucket.empty:
        return None
    strikes = np.sort(bucket["strike"].unique())
    payouts = []
    for settlement in strikes:
        call_payout = np.maximum(settlement - bucket.loc[bucket["type"] == "C", "strike"], 0) * bucket.loc[bucket["type"] == "C", "oi"]
        put_payout = np.maximum(bucket.loc[bucket["type"] == "P", "strike"] - settlement, 0) * bucket.loc[bucket["type"] == "P", "oi"]
        payouts.append(float(call_payout.sum() + put_payout.sum()))
    return float(strikes[int(np.argmin(payouts))])


def max_pain_by_expiry(chain: pd.DataFrame, limit: int = 4) -> list[dict[str, Any]]:
    """Return max pain for the nearest expiries."""
    expiries = sorted(chain["expiry"].dropna().unique())[:limit]
    rows = []
    for expiry in expiries:
        rows.append({"expiry": pd.Timestamp(expiry).date().isoformat(), "max_pain": compute_max_pain(chain, expiry)})
    return rows


def compute_term_slope(chain: pd.DataFrame) -> float | None:
    """Compute back minus front ATM implied-vol slope from nearest two expiries."""
    if chain.empty or "underlying_price" not in chain:
        return None
    spot = chain["underlying_price"].dropna().median()
    if pd.isna(spot):
        return None
    expiries = sorted(chain["expiry"].dropna().unique())
    if len(expiries) < 2:
        return None

    atm_ivs = []
    for expiry in expiries[:2]:
        bucket = chain[(chain["expiry"] == expiry) & chain["mark_iv"].notna()].copy()
        if bucket.empty:
            continue
        row = bucket.iloc[(bucket["strike"] - spot).abs().argmin()]
        atm_ivs.append(float(row["mark_iv"]))
    if len(atm_ivs) < 2:
        return None
    return float(atm_ivs[1] - atm_ivs[0])


def summarize_snapshot(chain: pd.DataFrame, spot: float, dvol: float | None) -> dict[str, Any]:
    """Summarize one live option-chain snapshot into weekly point-in-time metrics."""
    if chain.empty:
        return {}
    pcr = compute_pcr(chain)
    gex = compute_gex(chain, spot)
    expiries = sorted(chain["expiry"].dropna().unique())
    front_max_pain = compute_max_pain(chain, expiries[0]) if expiries else None
    return {
        "date": pd.Timestamp.utcnow().normalize(),
        "opt_oi_total": float(chain["oi"].sum()),
        "opt_pcr_oi": pcr["pcr_oi"],
        "opt_pcr_vol": pcr["pcr_vol"],
        "opt_gex_net": gex["net_gex"],
        "opt_gamma_flip": gex["gamma_flip_level"],
        "opt_skew_25d_30d": compute_skew(chain),
        "opt_maxpain_front": front_max_pain,
        "opt_dvol": dvol,
        "opt_term_slope": compute_term_slope(chain),
    }
