#!/usr/bin/env python3
"""
Generate a BTC price chart with a separate full-model conviction oscillator.

BTC price is plotted in its own top panel on a log scale. The full 14-indicator
conviction percentage is plotted as a separate oscillator in the bottom panel.
When only historical anchor scores are available, the oscillator plots those
anchor points instead of implying weekly observations. Both panels share the
same x-axis. Only the validated full-model extreme score zones are shaded in the
oscillator:

  - 0-30%: Historical Tops
  - 85-100%: Generational Bottoms

The 31-84% no-signal range is intentionally left uncolored.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Tuple

FULL_INDICATOR_WEIGHTS = {
    "globalM2": 1,
    "financialConditions": 1,
    "mvrvZScore": 3,
    "realizedPrice": 3,
    "twoHundredWeekMA": 3,
    "reserveRisk": 2,
    "puellMultiple": 2,
    "ahr999": 1,
    "hashRibbons": 3,
    "sopr": 2,
    "lthSupply": 2,
    "weeklyHigherLow": 1,
    "stablecoinSupply": 1,
    "halvingCycle": 2,
}
FULL_MAX_SCORE = sum(FULL_INDICATOR_WEIGHTS.values())
SIGNAL_VALUES = {"bullish": 1, "neutral": 0, "bearish": -1}


def load_backtest_module() -> Any:
    script_path = Path(__file__).with_name("backtest_midcycle.py")
    spec = importlib.util.spec_from_file_location("backtest_midcycle", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["backtest_midcycle"] = module
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BTC price and full conviction score SVG chart.")
    parser.add_argument("--start", default="2010-01-01", help="Chart start date, YYYY-MM-DD. Default: 2010-01-01")
    parser.add_argument("--cache-dir", default="data/backtest_cache", help="Local data cache directory.")
    parser.add_argument("--refresh", action="store_true", help="Re-download cached source data before plotting.")
    parser.add_argument(
        "--score-csv",
        default="data/full_conviction_anchors.csv",
        help=(
            "CSV containing historical full-model conviction data. "
            "Use date plus score_pct/conviction_score/percentage, or date plus all 14 indicator status columns."
        ),
    )
    parser.add_argument("--output", default="public/btc-conviction-chart.svg", help="Output SVG path.")
    return parser.parse_args()


def nice_log_ticks(min_price: float, max_price: float) -> List[float]:
    ticks = []
    lower_power = math.floor(math.log10(min_price))
    upper_power = math.ceil(math.log10(max_price))
    for power in range(lower_power, upper_power + 1):
        for multiplier in (1, 2, 5):
            value = multiplier * (10 ** power)
            if min_price <= value <= max_price:
                ticks.append(value)
    return ticks


def fmt_price(value: float) -> str:
    if value >= 1000:
        return f"${value / 1000:.0f}K"
    if value >= 1:
        return f"${value:,.0f}"
    if value >= 0.01:
        return f"${value:.2f}"
    if value >= 0.001:
        return f"${value:.3f}"
    return f"${value:.4f}"


def line_path(points: Iterable[Tuple[float, float]]) -> str:
    commands = []
    for index, (x, y) in enumerate(points):
        command = "M" if index == 0 else "L"
        commands.append(f"{command}{x:.2f},{y:.2f}")
    return " ".join(commands)


def js_round(series: Any, deps: Any) -> Any:
    return deps.np.floor(series + 0.5)


def find_date_column(columns: Iterable[str]) -> str:
    for candidate in ("date", "time", "week", "timestamp"):
        if candidate in columns:
            return candidate
    raise RuntimeError("Score CSV must include a date/time column named date, time, week, or timestamp.")


def load_full_score_history(deps: Any, score_csv: Path) -> Any:
    pd = deps.pd

    if not score_csv.exists():
        raise RuntimeError(
            f"Full conviction history file not found: {score_csv}\n\n"
            "This chart now requires historical FULL-model conviction scores. "
            "The repo currently only has a current full-model snapshot in public/indicator-data.json; "
            "it does not contain historical all-14-indicator readings.\n\n"
            "Create a CSV with either:\n"
            "  date,score_pct\n"
            "or:\n"
            "  date,globalM2,financialConditions,mvrvZScore,realizedPrice,twoHundredWeekMA,"
            "reserveRisk,puellMultiple,ahr999,hashRibbons,sopr,lthSupply,weeklyHigherLow,"
            "stablecoinSupply,halvingCycle\n\n"
            "Indicator values must be bullish, neutral, or bearish."
        )

    raw = pd.read_csv(score_csv)
    date_column = find_date_column(raw.columns)
    raw[date_column] = pd.to_datetime(raw[date_column], errors="coerce")
    raw = raw.dropna(subset=[date_column]).sort_values(date_column)

    direct_score_columns = [
        column
        for column in ("score_pct", "conviction_score", "convictionScore", "percentage", "score")
        if column in raw.columns
    ]
    if direct_score_columns:
        score_column = direct_score_columns[0]
        raw["convictionScorePct"] = pd.to_numeric(raw[score_column], errors="coerce")
    else:
        missing = [indicator for indicator in FULL_INDICATOR_WEIGHTS if indicator not in raw.columns]
        if missing:
            raise RuntimeError(
                "Score CSV must include either a score_pct-like column or all 14 indicator status columns. "
                f"Missing indicator columns: {', '.join(missing)}"
            )

        raw_score = 0
        for indicator, weight in FULL_INDICATOR_WEIGHTS.items():
            values = raw[indicator].astype(str).str.strip().str.lower()
            invalid = sorted(set(values.dropna()) - set(SIGNAL_VALUES))
            if invalid:
                raise RuntimeError(f"Invalid values in {indicator}: {', '.join(invalid)}")
            raw_score = raw_score + values.map(SIGNAL_VALUES) * weight
        raw["convictionScorePct"] = js_round((raw_score + FULL_MAX_SCORE) / (2 * FULL_MAX_SCORE) * 100, deps)

    raw = raw.dropna(subset=["convictionScorePct"])
    raw = raw[(raw["convictionScorePct"] >= 0) & (raw["convictionScorePct"] <= 100)]
    if len(raw) < 2:
        raise RuntimeError("Need at least two historical full conviction score rows to draw an oscillator.")

    output_columns = [date_column, "convictionScorePct"]
    if "event" in raw.columns:
        output_columns.append("event")
    return raw[output_columns].rename(columns={date_column: "time"}).set_index("time")


def build_chart_data(deps: Any, coinmetrics: Any, full_scores: Any, start: str) -> Tuple[Any, Any]:
    pd = deps.pd

    scores = full_scores.loc[full_scores.index >= pd.Timestamp(start)].sort_index().copy()
    if len(scores) == 0:
        raise RuntimeError("No full conviction score rows remain after applying the start date.")

    chart_start = min(pd.Timestamp(start), scores.index.min())
    chart_end = max(coinmetrics.index.max(), scores.index.max())
    prices = coinmetrics[["PriceUSD"]].dropna().sort_index()
    prices = prices.loc[(prices.index >= chart_start) & (prices.index <= chart_end)].copy()
    if len(prices) == 0:
        raise RuntimeError("No BTC price rows available for the requested chart range.")

    score_rows = scores.reset_index()
    if score_rows.columns[0] != "time":
        score_rows = score_rows.rename(columns={score_rows.columns[0]: "time"})
    price_rows = prices.reset_index()
    if price_rows.columns[0] != "time":
        price_rows = price_rows.rename(columns={price_rows.columns[0]: "time"})
    merged_scores = pd.merge_asof(score_rows, price_rows, on="time", direction="backward")
    merged_scores = merged_scores.dropna(subset=["PriceUSD", "convictionScorePct"]).set_index("time")
    if len(merged_scores) == 0:
        raise RuntimeError("No chartable conviction rows after joining full scores to BTC price data.")

    return prices, merged_scores


def generate_svg(price_df: Any, score_df: Any, output_path: Path) -> None:
    width = 1600
    height = 1040
    margin_left = 115
    margin_right = 70
    margin_top = 105
    margin_bottom = 105
    price_h = 500
    oscillator_gap = 82
    oscillator_h = 260
    plot_w = width - margin_left - margin_right
    plot_x2 = margin_left + plot_w
    price_y1 = margin_top
    price_y2 = price_y1 + price_h
    oscillator_y1 = price_y2 + oscillator_gap
    oscillator_y2 = oscillator_y1 + oscillator_h

    start_ts = min(price_df.index.min(), score_df.index.min()).timestamp()
    end_ts = max(price_df.index.max(), score_df.index.max()).timestamp()
    min_price = max(0.0001, float(price_df["PriceUSD"].min()) * 0.8)
    max_price = float(price_df["PriceUSD"].max()) * 1.2
    log_min = math.log10(min_price)
    log_max = math.log10(max_price)

    def x_scale(timestamp: Any) -> float:
        return margin_left + (timestamp.timestamp() - start_ts) / (end_ts - start_ts) * plot_w

    def price_y(price: float) -> float:
        return price_y2 - (math.log10(price) - log_min) / (log_max - log_min) * price_h

    def score_y(score: float) -> float:
        return oscillator_y2 - score / 100 * oscillator_h

    price_points = [(x_scale(index), price_y(float(row.PriceUSD))) for index, row in price_df.iterrows()]
    score_points = [(x_scale(index), score_y(float(row.convictionScorePct))) for index, row in score_df.iterrows()]

    price_ticks = nice_log_ticks(min_price, max_price)
    score_ticks = [0, 30, 50, 85, 100]
    start_year = min(price_df.index.min().year, score_df.index.min().year)
    end_year = max(price_df.index.max().year, score_df.index.max().year)
    year_ticks = list(range(start_year, end_year + 1))

    generational_y1 = score_y(100)
    generational_y2 = score_y(85)
    top_zone_y1 = score_y(30)
    top_zone_y2 = score_y(0)

    latest_price = price_df.iloc[-1]
    latest_score = score_df.iloc[-1]
    latest_date = max(price_df.index[-1], score_df.index[-1]).strftime("%Y-%m-%d")
    title = "BTC Price and Full Conviction Oscillator"
    subtitle = (
        f"{min(price_df.index.min(), score_df.index.min()).strftime('%Y-%m-%d')} to {latest_date}. "
        "BTC price uses full history; oscillator uses full-model conviction anchor scores."
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f"<title>{html.escape(title)}</title>",
        f"<desc>{html.escape(subtitle)}</desc>",
        "<defs>",
        f'<clipPath id="priceClip"><rect x="{margin_left}" y="{price_y1}" width="{plot_w}" height="{price_h}"/></clipPath>',
        f'<clipPath id="oscillatorClip"><rect x="{margin_left}" y="{oscillator_y1}" width="{plot_w}" height="{oscillator_h}"/></clipPath>',
        '<marker id="arrowGreen" markerWidth="12" markerHeight="12" refX="6" refY="6" orient="auto" markerUnits="strokeWidth">',
        '<path d="M 0 0 L 12 6 L 0 12 z" fill="#10b981"/>',
        "</marker>",
        '<marker id="arrowRed" markerWidth="12" markerHeight="12" refX="6" refY="6" orient="auto" markerUnits="strokeWidth">',
        '<path d="M 0 0 L 12 6 L 0 12 z" fill="#ef4444"/>',
        "</marker>",
        "</defs>",
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        f'<text x="{margin_left}" y="44" font-family="Inter, Arial, sans-serif" font-size="30" font-weight="700" fill="#0f172a">{html.escape(title)}</text>',
        f'<text x="{margin_left}" y="74" font-family="Inter, Arial, sans-serif" font-size="15" fill="#475569">{html.escape(subtitle)}</text>',
        f'<text x="{margin_left}" y="{price_y1 - 18}" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="700" fill="#1e40af">BTC price, log scale</text>',
        f'<text x="{margin_left}" y="{oscillator_y1 - 18}" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="700" fill="#b45309">Full conviction oscillator</text>',
        f'<rect x="{margin_left}" y="{price_y1}" width="{plot_w}" height="{price_h}" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>',
        f'<rect x="{margin_left}" y="{oscillator_y1}" width="{plot_w}" height="{oscillator_h}" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>',
        f'<rect x="{margin_left}" y="{generational_y1:.2f}" width="{plot_w}" height="{generational_y2 - generational_y1:.2f}" fill="#10b981" opacity="0.16"/>',
        f'<rect x="{margin_left}" y="{top_zone_y1:.2f}" width="{plot_w}" height="{top_zone_y2 - top_zone_y1:.2f}" fill="#ef4444" opacity="0.14"/>',
    ]

    for tick in price_ticks:
        y = price_y(tick)
        parts.append(f'<line x1="{margin_left}" x2="{plot_x2}" y1="{y:.2f}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(f'<text x="{margin_left - 14}" y="{y + 5:.2f}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="13" fill="#475569">{fmt_price(tick)}</text>')

    for tick in score_ticks:
        y = score_y(tick)
        dash = "6 6" if tick in (30, 85) else "3 7"
        parts.append(f'<line x1="{margin_left}" x2="{plot_x2}" y1="{y:.2f}" y2="{y:.2f}" stroke="#94a3b8" stroke-width="1" stroke-dasharray="{dash}" opacity="0.55"/>')
        parts.append(f'<text x="{plot_x2 + 14}" y="{y + 5:.2f}" font-family="Inter, Arial, sans-serif" font-size="13" fill="#475569">{tick}%</text>')

    for year in year_ticks:
        dt = datetime(year, 1, 1)
        tick_ts = min(max(dt.timestamp(), start_ts), end_ts)
        x = margin_left + (tick_ts - start_ts) / (end_ts - start_ts) * plot_w
        parts.append(f'<line x1="{x:.2f}" x2="{x:.2f}" y1="{price_y1}" y2="{price_y2}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(f'<line x1="{x:.2f}" x2="{x:.2f}" y1="{oscillator_y1}" y2="{oscillator_y2}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(f'<text x="{x:.2f}" y="{oscillator_y2 + 34}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="14" fill="#334155">{year}</text>')

    parts.extend(
        [
            f'<path d="{line_path(price_points)}" clip-path="url(#priceClip)" fill="none" stroke="#2563eb" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"/>',
            f'<path d="{line_path(score_points)}" clip-path="url(#oscillatorClip)" fill="none" stroke="#f59e0b" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" stroke-dasharray="7 7" opacity="0.8"/>',
            f'<text x="{margin_left + 12}" y="{generational_y2 - 10:.2f}" font-family="Inter, Arial, sans-serif" font-size="13" fill="#047857">85-100% Generational Bottoms</text>',
            f'<text x="{margin_left + 12}" y="{top_zone_y1 + 22:.2f}" font-family="Inter, Arial, sans-serif" font-size="13" fill="#b91c1c">0-30% Historical Tops</text>',
            f'<text x="{plot_x2}" y="{price_y1 - 18}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="13" fill="#475569">Latest BTC: {fmt_price(float(latest_price.PriceUSD))}</text>',
            f'<text x="{plot_x2}" y="{oscillator_y1 - 18}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="13" fill="#475569">Latest anchor: {int(latest_score.convictionScorePct)}%</text>',
            f'<text x="{margin_left - 78}" y="{price_y1 + price_h / 2:.2f}" transform="rotate(-90 {margin_left - 78} {price_y1 + price_h / 2:.2f})" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" fill="#475569">BTC price (USD)</text>',
            f'<text x="{plot_x2 + 52}" y="{oscillator_y1 + oscillator_h / 2:.2f}" transform="rotate(90 {plot_x2 + 52} {oscillator_y1 + oscillator_h / 2:.2f})" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" fill="#475569">Conviction %</text>',
            f'<text x="{width / 2:.0f}" y="{height - 24}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" fill="#64748b">Full 14-indicator conviction anchor scores. Dashed oscillator connects anchor points only; 31-84% is intentionally unshaded.</text>',
        ]
    )

    for idx, (timestamp, row) in enumerate(score_df.iterrows()):
        x = x_scale(timestamp)
        y = score_y(float(row.convictionScorePct))
        fill = "#10b981" if row.convictionScorePct >= 85 else "#ef4444" if row.convictionScorePct <= 30 else "#f59e0b"
        price_anchor_y = price_y(float(row.PriceUSD))
        if row.convictionScorePct >= 85:
            arrow_start_y = min(price_anchor_y + 80, price_y2 - 14)
            arrow_end_y = min(price_anchor_y + 18, price_y2 - 8)
            parts.append(
                f'<line x1="{x:.2f}" y1="{arrow_start_y:.2f}" x2="{x:.2f}" y2="{arrow_end_y:.2f}" '
                f'stroke="#10b981" stroke-width="2.8" marker-end="url(#arrowGreen)" opacity="0.95"/>'
            )
            parts.append(
                f'<text x="{x:.2f}" y="{max(arrow_start_y - 8, price_y1 + 18):.2f}" text-anchor="middle" '
                f'font-family="Inter, Arial, sans-serif" font-size="11" font-weight="700" fill="#047857">BUY {int(row.convictionScorePct)}%</text>'
            )
        elif row.convictionScorePct <= 30:
            arrow_start_y = max(price_anchor_y - 80, price_y1 + 14)
            arrow_end_y = max(price_anchor_y - 18, price_y1 + 8)
            parts.append(
                f'<line x1="{x:.2f}" y1="{arrow_start_y:.2f}" x2="{x:.2f}" y2="{arrow_end_y:.2f}" '
                f'stroke="#ef4444" stroke-width="2.8" marker-end="url(#arrowRed)" opacity="0.95"/>'
            )
            parts.append(
                f'<text x="{x:.2f}" y="{min(arrow_start_y + 18, price_y2 - 10):.2f}" text-anchor="middle" '
                f'font-family="Inter, Arial, sans-serif" font-size="11" font-weight="700" fill="#b91c1c">SELL {int(row.convictionScorePct)}%</text>'
            )
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6.5" fill="{fill}" stroke="#0f172a" stroke-width="1.2"/>')
        event = getattr(row, "event", "")
        if event and len(score_df) <= 16:
            label_y_offset = -12 if idx % 2 == 0 else 22
            label_anchor = "middle"
            label = f"{event} {int(row.convictionScorePct)}%"
            parts.append(f'<text x="{x:.2f}" y="{y + label_y_offset:.2f}" text-anchor="{label_anchor}" font-family="Inter, Arial, sans-serif" font-size="10.5" fill="#334155">{html.escape(label)}</text>')

    parts.append("</svg>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    args = parse_args()
    backtest = load_backtest_module()
    deps = backtest.load_runtime_deps()
    cache_dir = Path(args.cache_dir)
    backtest.ensure_cache_dir(cache_dir)

    full_scores = load_full_score_history(deps, Path(args.score_csv))
    coinmetrics = backtest.load_coinmetrics(deps, cache_dir, args.refresh)
    price_df, score_df = build_chart_data(deps, coinmetrics, full_scores, args.start)

    output_path = Path(args.output)
    generate_svg(price_df, score_df, output_path)
    print(f"Wrote {output_path}")
    print(f"Price rows: {len(price_df)}")
    print(f"Conviction anchors: {len(score_df)}")
    print(f"Range: {min(price_df.index.min(), score_df.index.min()).date()} to {max(price_df.index.max(), score_df.index.max()).date()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
