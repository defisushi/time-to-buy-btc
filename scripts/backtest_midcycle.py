#!/usr/bin/env python3
"""
Backtest partial BTC conviction-score buckets and mid-cycle inflections.

This script reconstructs the subset of the live Bitcoin conviction score that
can be derived from free historical data:

  - twoHundredWeekMA, weight 3
  - mvrvZScore, weight 3
  - puellMultiple, weight 2
  - stablecoinSupply, weight 1
  - halvingCycle, weight 2

It intentionally does not reconstruct indicators that need paid, proprietary,
or specialized data. The partial score has 11 max weight points, while the live
model has 14 indicators and 27 max weight points. Partial scores are therefore
only useful for this internal backtest; do not compare them directly to the
live model's 0-30%, 31-84%, and 85-100% tier boundaries.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


COINMETRICS_BTC_CSV = "https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv"
STABLECOIN_ENDPOINTS = [
    "https://stablecoins.llama.fi/stablecoincharts/all",
    "https://stablecoins.llama.fi/stablecoinchart/all",
    "https://api.llama.fi/stablecoincharts/all",
    "https://api.llama.fi/stablecoinchart/all",
]

FULL_MODEL_INDICATORS = 14
FULL_MODEL_MAX_SCORE = 27

INDICATOR_WEIGHTS = {
    "twoHundredWeekMA": 3,
    "mvrvZScore": 3,
    "puellMultiple": 2,
    "stablecoinSupply": 1,
    "halvingCycle": 2,
}
MAX_PARTIAL_SCORE = sum(INDICATOR_WEIGHTS.values())
SIGNAL_VALUES = {"bullish": 1, "neutral": 0, "bearish": -1}

HALVINGS = [
    ("2012-11-28", "Nov 28 2012"),
    ("2016-07-09", "Jul 9 2016"),
    ("2020-05-11", "May 11 2020"),
    ("2024-04-19", "Apr 19 2024"),
]

MISSING_INDICATORS = [
    "globalM2",
    "financialConditions",
    "realizedPrice",
    "reserveRisk",
    "ahr999",
    "hashRibbons",
    "sopr",
    "lthSupply",
    "weeklyHigherLow",
]


@dataclass
class RuntimeDeps:
    pd: Any
    np: Any
    requests: Any


def load_runtime_deps() -> RuntimeDeps:
    try:
        import numpy as np
        import pandas as pd
        import requests
    except ModuleNotFoundError as exc:
        missing = exc.name or "a required package"
        print(
            f"Missing Python package: {missing}\n\n"
            "Install the allowed runtime dependencies, then rerun:\n"
            "  python3 -m pip install pandas numpy requests",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    return RuntimeDeps(pd=pd, np=np, requests=requests)


# ---------------------------------------------------------------------------
# CLI and local cache helpers
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest free-data BTC conviction-score buckets and candidate mid-cycle tier boundaries."
    )
    parser.add_argument("--start", default="2015-01-01", help="Backtest start date, YYYY-MM-DD. Default: 2015-01-01")
    parser.add_argument("--cache-dir", default="data/backtest_cache", help="Local data cache directory.")
    parser.add_argument("--refresh", action="store_true", help="Re-download cached CoinMetrics and DefiLlama data.")
    parser.add_argument("--csv", default=None, help="Optional path for writing bucket stats as CSV.")
    return parser.parse_args()


def ensure_cache_dir(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)


def download_file(requests: Any, url: str, path: Path, refresh: bool) -> None:
    if path.exists() and not refresh:
        return

    print(f"Downloading {url}")
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    path.write_bytes(response.content)


def load_json_from_cache_or_url(requests: Any, urls: List[str], path: Path, refresh: bool) -> Tuple[Any, str]:
    if path.exists() and not refresh:
        return json.loads(path.read_text()), f"cache:{path}"

    errors = []
    for url in urls:
        try:
            print(f"Downloading {url}")
            response = requests.get(url, timeout=45)
            response.raise_for_status()
            data = response.json()
            path.write_text(json.dumps(data))
            return data, url
        except Exception as exc:  # Try documented and legacy DefiLlama spellings.
            errors.append(f"{url}: {exc}")

    raise RuntimeError("Could not fetch DefiLlama stablecoin history:\n" + "\n".join(errors))


# ---------------------------------------------------------------------------
# Source data loading
# ---------------------------------------------------------------------------


def load_coinmetrics(deps: RuntimeDeps, cache_dir: Path, refresh: bool) -> Any:
    path = cache_dir / "coinmetrics_btc.csv"
    download_file(deps.requests, COINMETRICS_BTC_CSV, path, refresh)

    required = ["time", "PriceUSD", "CapMVRVCur", "IssTotUSD"]
    df = deps.pd.read_csv(path, usecols=required, parse_dates=["time"])
    df = df.sort_values("time").set_index("time")
    for column in required[1:]:
        df[column] = deps.pd.to_numeric(df[column], errors="coerce")
    return df


def parse_stablecoin_rows(deps: RuntimeDeps, raw: Any) -> Any:
    pd = deps.pd

    rows = raw.get("data", raw) if isinstance(raw, dict) else raw
    parsed = []
    for row in rows:
        if not isinstance(row, dict) or "date" not in row:
            continue

        raw_date = row["date"]
        if isinstance(raw_date, (int, float)):
            date_value = pd.to_datetime(int(raw_date), unit="s", utc=True).tz_localize(None)
        elif isinstance(raw_date, str) and raw_date.isdigit():
            date_value = pd.to_datetime(int(raw_date), unit="s", utc=True).tz_localize(None)
        else:
            date_value = pd.to_datetime(str(raw_date), errors="coerce")
        if pd.isna(date_value):
            continue

        total = row.get("totalCirculating") or row.get("totalCirculatingUSD") or row.get("total")
        if isinstance(total, dict):
            value = total.get("peggedUSD") or total.get("usd") or total.get("USD")
        else:
            value = total
        value = pd.to_numeric(value, errors="coerce")
        if pd.isna(value):
            continue

        parsed.append({"time": date_value.normalize(), "StablecoinSupplyUSD": float(value)})

    if not parsed:
        raise RuntimeError("DefiLlama response did not contain usable stablecoin supply rows.")

    df = pd.DataFrame(parsed).drop_duplicates("time").sort_values("time").set_index("time")
    return df


def load_stablecoins(deps: RuntimeDeps, cache_dir: Path, refresh: bool) -> Tuple[Any, str]:
    raw, source = load_json_from_cache_or_url(deps.requests, STABLECOIN_ENDPOINTS, cache_dir / "defillama_stablecoins.json", refresh)
    return parse_stablecoin_rows(deps, raw), source


# ---------------------------------------------------------------------------
# Indicator reconstruction
# ---------------------------------------------------------------------------


def js_round(series: Any, deps: RuntimeDeps) -> Any:
    return deps.np.floor(series + 0.5).astype("Int64")


def signal_to_score(series: Any) -> Any:
    return series.map(SIGNAL_VALUES)


def classify_two_hundred_week_ma(df: Any, deps: RuntimeDeps) -> Any:
    np = deps.np
    ratio = df["PriceUSD"] / df["MA200W"]
    return deps.pd.Series(
        np.select(
            [ratio <= 1.0, (ratio > 1.0) & (ratio <= 1.2), ratio > 1.2],
            ["bullish", "neutral", "bearish"],
            default=None,
        ),
        index=df.index,
    )


def classify_mvrv_z(df: Any, deps: RuntimeDeps) -> Any:
    np = deps.np
    return deps.pd.Series(
        np.select(
            [df["MVRVZ"] < 0.5, (df["MVRVZ"] >= 0.5) & (df["MVRVZ"] <= 2.5), df["MVRVZ"] > 2.5],
            ["bullish", "neutral", "bearish"],
            default=None,
        ),
        index=df.index,
    )


def classify_puell(df: Any, deps: RuntimeDeps) -> Any:
    np = deps.np
    return deps.pd.Series(
        np.select(
            [df["PuellMultiple"] < 0.5, (df["PuellMultiple"] >= 0.5) & (df["PuellMultiple"] <= 1.5), df["PuellMultiple"] > 1.5],
            ["bullish", "neutral", "bearish"],
            default=None,
        ),
        index=df.index,
    )


def classify_stablecoins(df: Any, deps: RuntimeDeps) -> Any:
    np = deps.np
    return deps.pd.Series(
        np.select(
            [
                df["Stablecoin90DChangePct"] > 3.0,
                (df["Stablecoin90DChangePct"] >= 0.0) & (df["Stablecoin90DChangePct"] <= 3.0),
                df["Stablecoin90DChangePct"] < 0.0,
            ],
            ["bullish", "neutral", "bearish"],
            default=None,
        ),
        index=df.index,
    )


def classify_halving(weekly_index: Any, deps: RuntimeDeps) -> Any:
    pd = deps.pd
    halving_dates = [pd.Timestamp(date) for date, _label in HALVINGS]

    signals = []
    months_since_values = []
    for timestamp in weekly_index:
        previous = [date for date in halving_dates if date <= timestamp]
        if not previous:
            signals.append(None)
            months_since_values.append(None)
            continue

        months_since = (timestamp - previous[-1]).days / 30.44
        months_since_values.append(months_since)
        if 6 <= months_since <= 18:
            signals.append("bullish")
        elif months_since < 6 or months_since <= 30:
            signals.append("neutral")
        else:
            signals.append("bearish")

    return pd.Series(signals, index=weekly_index), pd.Series(months_since_values, index=weekly_index)


def build_weekly_scores(deps: RuntimeDeps, coinmetrics: Any, stablecoins: Any) -> Any:
    pd = deps.pd

    daily = coinmetrics.copy()

    # MVRV Z is derived without lookahead: expanding mean/std use only data up
    # to the current date. The first year is skipped to avoid unstable z-scores.
    daily["MVRVMean"] = daily["CapMVRVCur"].expanding(min_periods=365).mean()
    daily["MVRVStd"] = daily["CapMVRVCur"].expanding(min_periods=365).std()
    daily["MVRVZ"] = (daily["CapMVRVCur"] - daily["MVRVMean"]) / daily["MVRVStd"]

    # Puell Multiple follows the prompt: daily issuance divided by its 365-day
    # rolling average, then sampled weekly.
    daily["Iss365MA"] = daily["IssTotUSD"].rolling(365, min_periods=365).mean()
    daily["PuellMultiple"] = daily["IssTotUSD"] / daily["Iss365MA"]

    weekly = daily[["PriceUSD", "MVRVZ", "PuellMultiple"]].resample("W-FRI").last()
    weekly["MA200W"] = weekly["PriceUSD"].rolling(200, min_periods=200).mean()

    stable_daily = stablecoins.resample("D").last().ffill()
    stable_daily["Stablecoin90DChangePct"] = stable_daily["StablecoinSupplyUSD"].pct_change(periods=90) * 100
    stable_weekly = stable_daily[["StablecoinSupplyUSD", "Stablecoin90DChangePct"]].resample("W-FRI").last()

    weekly = weekly.join(stable_weekly, how="left")
    halving_signal, months_since_halving = classify_halving(weekly.index, deps)
    weekly["halvingCycle"] = halving_signal
    weekly["MonthsSinceHalving"] = months_since_halving

    weekly["twoHundredWeekMA"] = classify_two_hundred_week_ma(weekly, deps)
    weekly["mvrvZScore"] = classify_mvrv_z(weekly, deps)
    weekly["puellMultipleSignal"] = classify_puell(weekly, deps)
    weekly["stablecoinSupply"] = classify_stablecoins(weekly, deps)

    score_columns = {
        "twoHundredWeekMA": "twoHundredWeekMA",
        "mvrvZScore": "mvrvZScore",
        "puellMultiple": "puellMultipleSignal",
        "stablecoinSupply": "stablecoinSupply",
        "halvingCycle": "halvingCycle",
    }
    for indicator, column in score_columns.items():
        weekly[f"{indicator}Score"] = signal_to_score(weekly[column]) * INDICATOR_WEIGHTS[indicator]

    weighted_columns = [f"{indicator}Score" for indicator in score_columns]
    weekly["rawPartialScore"] = weekly[weighted_columns].sum(axis=1, min_count=len(weighted_columns))
    weekly["partialScorePct"] = js_round((weekly["rawPartialScore"] + MAX_PARTIAL_SCORE) / (2 * MAX_PARTIAL_SCORE) * 100, deps)

    weekly["return3m"] = weekly["PriceUSD"].shift(-13) / weekly["PriceUSD"] - 1
    weekly["return6m"] = weekly["PriceUSD"].shift(-26) / weekly["PriceUSD"] - 1
    weekly["return12m"] = weekly["PriceUSD"].shift(-52) / weekly["PriceUSD"] - 1

    return weekly


def build_weekly_dataset(deps: RuntimeDeps, coinmetrics: Any, stablecoins: Any, start: str) -> Tuple[Any, Dict[str, Any]]:
    pd = deps.pd
    weekly = build_weekly_scores(deps, coinmetrics, stablecoins)

    needed = [
        "PriceUSD",
        "MA200W",
        "MVRVZ",
        "PuellMultiple",
        "Stablecoin90DChangePct",
        "halvingCycle",
        "partialScorePct",
        "return3m",
        "return6m",
        "return12m",
    ]
    valid = weekly.loc[weekly.index >= pd.Timestamp(start)].dropna(subset=needed).copy()
    valid["scoreBucketLow"] = (valid["partialScorePct"].astype(int) // 5) * 5
    valid["scoreBucketHigh"] = valid["scoreBucketLow"] + 4
    valid.loc[valid["scoreBucketLow"] == 100, "scoreBucketHigh"] = 100
    valid["scoreBucket"] = valid["scoreBucketLow"].astype(str) + "-" + valid["scoreBucketHigh"].astype(str) + "%"

    metadata = {
        "coinmetrics_start": coinmetrics.index.min(),
        "coinmetrics_end": coinmetrics.index.max(),
        "stablecoin_start": stablecoins.index.min(),
        "stablecoin_end": stablecoins.index.max(),
        "weekly_start": valid.index.min() if len(valid) else None,
        "weekly_end": valid.index.max() if len(valid) else None,
        "excluded_recent_weeks": 52,
    }
    return valid, metadata


# ---------------------------------------------------------------------------
# Bucket statistics and inflection analysis
# ---------------------------------------------------------------------------


def summarize_buckets(deps: RuntimeDeps, weekly: Any) -> Any:
    pd = deps.pd
    all_buckets = pd.DataFrame({"scoreBucketLow": list(range(0, 101, 5))})
    all_buckets["scoreBucketHigh"] = all_buckets["scoreBucketLow"] + 4
    all_buckets.loc[all_buckets["scoreBucketLow"] == 100, "scoreBucketHigh"] = 100
    all_buckets["scoreBucket"] = all_buckets["scoreBucketLow"].astype(str) + "-" + all_buckets["scoreBucketHigh"].astype(str) + "%"

    grouped = weekly.groupby(["scoreBucketLow", "scoreBucketHigh", "scoreBucket"], observed=True)
    stats = grouped.agg(
        count=("partialScorePct", "size"),
        mean3m=("return3m", "mean"),
        median3m=("return3m", "median"),
        mean6m=("return6m", "mean"),
        median6m=("return6m", "median"),
        mean12m=("return12m", "mean"),
        median12m=("return12m", "median"),
        positive12m=("return12m", lambda series: (series > 0).mean()),
    ).reset_index()

    stats = all_buckets.merge(stats, on=["scoreBucketLow", "scoreBucketHigh", "scoreBucket"], how="left")
    stats["count"] = stats["count"].fillna(0).astype(int)
    return stats.sort_values("scoreBucketLow")


def find_inflections(stats: Any) -> List[Dict[str, Any]]:
    nonempty = stats[(stats["count"] > 0) & (stats["median12m"].notna())].sort_values("scoreBucketLow")
    rows = nonempty.to_dict("records")
    inflections = []

    for previous, current in zip(rows, rows[1:]):
        previous_value = previous["median12m"]
        current_value = current["median12m"]
        if previous_value == 0 or current_value == 0:
            continue
        if previous_value < 0 < current_value:
            direction = "negative to positive"
        elif previous_value > 0 > current_value:
            direction = "positive to negative"
        else:
            continue

        inflections.append(
            {
                "between": f"{previous['scoreBucket']} and {current['scoreBucket']}",
                "boundary": f"{previous['scoreBucketHigh']}% / {current['scoreBucketLow']}%",
                "direction": direction,
                "previous_median12m": previous_value,
                "current_median12m": current_value,
                "previous_count": previous["count"],
                "current_count": current["count"],
            }
        )
    return inflections


def format_return(value: Any) -> str:
    if value is None or value != value:
        return "n/a"
    return f"{value * 100:+.1f}%"


def format_positive(value: Any) -> str:
    if value is None or value != value:
        return "n/a"
    return f"{value * 100:.0f}%"


def print_data_summary(weekly: Any, metadata: Dict[str, Any], stablecoin_source: str) -> None:
    print("\nDATA SUMMARY")
    print(f"Weekly observations with all indicators and 52-week forward returns: {len(weekly)}")
    print(f"Weekly backtest range: {metadata['weekly_start'].date()} to {metadata['weekly_end'].date()}")
    print(f"CoinMetrics BTC data: {metadata['coinmetrics_start'].date()} to {metadata['coinmetrics_end'].date()}")
    print(f"DefiLlama stablecoin data: {metadata['stablecoin_start'].date()} to {metadata['stablecoin_end'].date()}")
    print(f"Stablecoin source used: {stablecoin_source}")
    print("Reconstructed indicators:")
    for name, weight in INDICATOR_WEIGHTS.items():
        print(f"  - {name} (weight {weight})")


def print_bucket_table(stats: Any) -> None:
    print("\nMAIN RESULTS TABLE")
    print(
        f"{'bucket':>8} | {'count':>5} | {'mean 3m':>8} | {'med 3m':>8} | "
        f"{'mean 6m':>8} | {'med 6m':>8} | {'mean 12m':>9} | {'med 12m':>8} | {'+12m':>5}"
    )
    print("-" * 92)
    for row in stats.to_dict("records"):
        print(
            f"{row['scoreBucket']:>8} | {row['count']:5d} | "
            f"{format_return(row['mean3m']):>8} | {format_return(row['median3m']):>8} | "
            f"{format_return(row['mean6m']):>8} | {format_return(row['median6m']):>8} | "
            f"{format_return(row['mean12m']):>9} | {format_return(row['median12m']):>8} | "
            f"{format_positive(row['positive12m']):>5}"
        )


def print_inflections(inflections: List[Dict[str, Any]], stats: Any) -> None:
    print("\nINFLECTION POINT ANALYSIS")
    if inflections:
        print("Median 12-month return sign changes by score bucket:")
        for item in inflections:
            print(
                f"  - {item['between']} ({item['boundary']}): {item['direction']} "
                f"[n={item['previous_count']} -> {item['current_count']}, "
                f"med12={format_return(item['previous_median12m'])} -> {format_return(item['current_median12m'])}]"
            )
        print("Treat these sign changes as candidate partial-score tier boundaries.")
        return

    nonempty = stats[(stats["count"] > 0) & (stats["median12m"].notna())].copy()
    if len(nonempty) == 0:
        print("No populated buckets were available for median 12-month return analysis.")
        return

    best = nonempty.sort_values("median12m", ascending=False).iloc[0]
    worst = nonempty.sort_values("median12m", ascending=True).iloc[0]
    print("No positive/negative median 12-month return crossover was found between adjacent populated buckets.")
    print(
        f"Strongest bucket: {best['scoreBucket']} with median 12m {format_return(best['median12m'])} "
        f"(n={int(best['count'])})."
    )
    print(
        f"Weakest bucket: {worst['scoreBucket']} with median 12m {format_return(worst['median12m'])} "
        f"(n={int(worst['count'])})."
    )


def print_disclaimer() -> None:
    print("\nIMPORTANT DISCLAIMER")
    print(
        f"This is a partial reconstruction using 5 of {FULL_MODEL_INDICATORS} indicators "
        f"({MAX_PARTIAL_SCORE} partial max score points vs {FULL_MODEL_MAX_SCORE} in the live model)."
    )
    print(
        "The missing 9 indicators require paid, proprietary, specialized, or manual data sources: "
        + ", ".join(MISSING_INDICATORS)
        + "."
    )
    print(
        "Partial scores are not directly comparable to the validated full-model tiers "
        "of 0-30%, 31-84%, and 85-100%. Use this only to study internal return-profile "
        "inflections in the free-data partial model."
    )


def write_csv(stats: Any, path: str) -> None:
    stats.to_csv(path, index=False)
    print(f"\nWrote CSV: {path}")


def main() -> int:
    started_at = time.time()
    args = parse_args()
    deps = load_runtime_deps()
    cache_dir = Path(args.cache_dir)
    ensure_cache_dir(cache_dir)

    print("BTC PARTIAL MID-CYCLE BACKTEST")
    print(f"Start date: {args.start}")
    print(f"Cache dir: {cache_dir}")
    print("No API keys required.")

    coinmetrics = load_coinmetrics(deps, cache_dir, args.refresh)
    stablecoins, stablecoin_source = load_stablecoins(deps, cache_dir, args.refresh)
    weekly, metadata = build_weekly_dataset(deps, coinmetrics, stablecoins, args.start)

    if len(weekly) == 0:
        raise RuntimeError("No weekly observations remain after applying indicator and 52-week forward-return filters.")

    stats = summarize_buckets(deps, weekly)
    inflections = find_inflections(stats)

    print_disclaimer()
    print_data_summary(weekly, metadata, stablecoin_source)
    print_bucket_table(stats)
    print_inflections(inflections, stats)

    if args.csv:
        write_csv(stats, args.csv)

    freshness = max(metadata["coinmetrics_end"], metadata["stablecoin_end"])
    runtime = time.time() - started_at
    print("\nRUNTIME AND FRESHNESS")
    print(f"Latest source-data date: {freshness.date()}")
    print(f"Runtime: {runtime:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
