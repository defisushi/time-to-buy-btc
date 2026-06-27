"""Configuration constants for the ETF/options weekly pipeline."""

from pathlib import Path

WEEK = "W-FRI"
TZ = "UTC"
ETF_TICKERS = ["IBIT", "FBTC", "ARKB", "BITB", "GBTC", "HODL", "BTCO", "EZBC", "BRRR", "BTCW"]
DERIBIT_BASE = "https://www.deribit.com/api/v2"
MAX_LAG_WEEKS = 8
GRANGER_MAX_LAG = 4

SIGNAL_WEIGHTS = {
    "etf_mom_4w": 1.25,
    "etf_net_1w": 1.0,
    "opt_skew_25d_30d": 0.75,
    "opt_pcr_oi": -0.75,
    "gamma_regime": 0.75,
    "trend": 1.0,
}
ZSCORE_CAP = 2.5

FEATURE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
WEEKLY_CSV = REPO_ROOT / "data" / "etf_options_weekly.csv"
OPTIONS_SNAPSHOT_JSON = REPO_ROOT / "data" / "options_snapshot_latest.json"
PUBLIC_JSON = REPO_ROOT / "public" / "etf-options-data.json"
