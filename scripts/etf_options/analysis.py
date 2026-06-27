"""Statistical summaries and weekly conviction signals."""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy import stats

from .config import GRANGER_MAX_LAG, MAX_LAG_WEEKS, SIGNAL_WEIGHTS, ZSCORE_CAP


DEFAULT_METRICS = ["etf_net_1w", "etf_mom_4w", "opt_pcr_oi", "opt_gex_net", "opt_skew_25d_30d", "opt_dvol"]


def _bh_fdr(pvals: list[float], alpha: float = 0.1) -> list[bool]:
    valid = [(idx, p) for idx, p in enumerate(pvals) if not np.isnan(p)]
    if not valid:
        return [False] * len(pvals)
    ordered = sorted(valid, key=lambda item: item[1])
    passed = [False] * len(pvals)
    threshold_idx = -1
    m = len(valid)
    for rank, (_, pval) in enumerate(ordered, start=1):
        if pval <= alpha * rank / m:
            threshold_idx = rank
    if threshold_idx > 0:
        cutoff = ordered[threshold_idx - 1][1]
        passed = [bool((not np.isnan(p)) and p <= cutoff) for p in pvals]
    return passed


def correlations(weekly: pd.DataFrame, target: str = "btc_ret_1w", metrics: Iterable[str] = DEFAULT_METRICS) -> list[dict[str, Any]]:
    """Compute Pearson/Spearman correlations for t, t+1, and t+2 target shifts."""
    rows: list[dict[str, Any]] = []
    for metric in metrics:
        if metric not in weekly or target not in weekly:
            continue
        for shift in [0, 1, 2]:
            joined = weekly[[metric, target]].copy()
            joined[target] = joined[target].shift(-shift)
            joined = joined.dropna()
            if len(joined) < 6:
                pearson = spearman = pval = np.nan
            else:
                pearson, pval = stats.pearsonr(joined[metric], joined[target])
                spearman, _ = stats.spearmanr(joined[metric], joined[target])
            rows.append({"metric": metric, "shift": shift, "pearson": pearson, "spearman": spearman, "pval": pval})
    flags = _bh_fdr([float(row["pval"]) if row["pval"] == row["pval"] else np.nan for row in rows])
    for row, flag in zip(rows, flags):
        row["fdr_pass"] = flag
    return rows


def lead_lag(weekly: pd.DataFrame, metrics: Iterable[str] = DEFAULT_METRICS, max_lag: int = MAX_LAG_WEEKS, target: str = "btc_ret_1w") -> list[dict[str, Any]]:
    """Cross-correlation rows over negative and positive lags for a heatmap."""
    rows: list[dict[str, Any]] = []
    for metric in metrics:
        if metric not in weekly or target not in weekly:
            continue
        best: tuple[int, float] | None = None
        metric_rows: list[dict[str, Any]] = []
        for lag in range(-max_lag, max_lag + 1):
            x = weekly[metric]
            y = weekly[target].shift(-lag)
            joined = pd.concat([x, y], axis=1).dropna()
            corr = float(joined.iloc[:, 0].corr(joined.iloc[:, 1])) if len(joined) >= 6 else np.nan
            metric_rows.append({"metric": metric, "lag": lag, "corr": corr})
            if not np.isnan(corr) and (best is None or abs(corr) > abs(best[1])):
                best = (lag, corr)
        interpretation = "insufficient history"
        if best is not None:
            interpretation = "metric leads BTC" if best[0] > 0 else "BTC leads metric" if best[0] < 0 else "same week"
        for row in metric_rows:
            row["peakLag"] = best[0] if best else None
            row["interpretation"] = interpretation
        rows.extend(metric_rows)
    return rows


def granger(weekly: pd.DataFrame, target: str, predictors: Iterable[str], max_lag: int = GRANGER_MAX_LAG) -> list[dict[str, Any]]:
    """Run small-sample Granger tests after differencing level-like series.

    With ETF history starting in 2024 and options history starting only from the first run,
    these p-values are underpowered and should be treated as exploratory.
    """
    try:
        from statsmodels.tsa.stattools import grangercausalitytests
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for predictor in predictors:
        if predictor not in weekly or target not in weekly:
            continue
        data = weekly[[target, predictor]].apply(pd.to_numeric, errors="coerce")
        for col in data.columns:
            if col in {"etf_cum", "btc_close"} or data[col].abs().median() > 10:
                data[col] = data[col].diff()
        data = data.dropna()
        if len(data) < max_lag * 4 + 8:
            continue
        try:
            result = grangercausalitytests(data[[target, predictor]], maxlag=max_lag, verbose=False)
            rows.append({"predictor": predictor, "direction": f"{predictor}-> {target}", "min_pval": min(result[lag][0]["ssr_ftest"][1] for lag in result)})
            reverse = grangercausalitytests(data[[predictor, target]], maxlag=max_lag, verbose=False)
            rows.append({"predictor": predictor, "direction": f"{target}-> {predictor}", "min_pval": min(reverse[lag][0]["ssr_ftest"][1] for lag in reverse)})
        except Exception:
            continue
    return rows


def rule_based_regime(weekly: pd.DataFrame) -> list[dict[str, Any]]:
    """Label each week by price trend and DVOL stress."""
    data = weekly.copy()
    data["ma20"] = data["btc_close"].rolling(20, min_periods=4).mean()
    dvol_pct = data["opt_dvol"].rank(pct=True) if "opt_dvol" in data else pd.Series(0.5, index=data.index)
    rows = []
    for _, row in data.iterrows():
        trend = "Bull" if row.get("btc_close", np.nan) >= row.get("ma20", np.nan) else "Bear"
        vol = "Stress" if dvol_pct.loc[row.name] >= 0.7 else "Calm"
        rows.append({"week_end": row["week_end"], "label": f"{trend}-{vol}"})
    return rows


def _zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    std = values.std()
    if not std or np.isnan(std):
        return pd.Series(0.0, index=series.index)
    return ((values - values.mean()) / std).clip(-ZSCORE_CAP, ZSCORE_CAP)


def _expanding_zscore(series: pd.Series, min_periods: int = 8) -> pd.Series:
    """Point-in-time z-score using only observations available up to each row."""
    values = pd.to_numeric(series, errors="coerce")
    mean = values.expanding(min_periods=min_periods).mean()
    std = values.expanding(min_periods=min_periods).std()
    zscore = ((values - mean) / std.replace(0, np.nan)).clip(-ZSCORE_CAP, ZSCORE_CAP)
    return zscore.fillna(0.0)


def _expanding_quantile(series: pd.Series, q: float, min_periods: int = 8) -> pd.Series:
    """Point-in-time expanding quantile for historical signal flags."""
    values = pd.to_numeric(series, errors="coerce")
    return values.expanding(min_periods=min_periods).quantile(q)


def weekly_conviction(weekly: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Build a weekly conviction score in [-100, 100] plus discrete signal flags."""
    weights = weights or SIGNAL_WEIGHTS
    data = weekly.copy()
    score = pd.Series(0.0, index=data.index)
    total_weight = 0.0
    for metric in ["etf_mom_4w", "etf_net_1w", "opt_skew_25d_30d"]:
        if metric in data:
            weight = weights.get(metric, 0)
            score += _expanding_zscore(data[metric]) * weight
            total_weight += abs(weight)
    if "opt_pcr_oi" in data:
        weight = abs(weights.get("opt_pcr_oi", -0.75))
        score += -_expanding_zscore(data["opt_pcr_oi"]) * weight
        total_weight += weight
    if {"btc_close", "opt_gamma_flip"}.issubset(data.columns):
        btc_close = pd.to_numeric(data["btc_close"], errors="coerce")
        gamma_flip = pd.to_numeric(data["opt_gamma_flip"], errors="coerce")
        valid_gamma = btc_close.notna() & gamma_flip.notna()
        gamma_regime = np.where(valid_gamma, np.where(btc_close >= gamma_flip, 1.0, -1.0), 0.0)
        weight = weights.get("gamma_regime", 0.75)
        score += gamma_regime * weight
        total_weight += abs(weight)
        data["gamma_regime"] = np.where(valid_gamma, np.where(gamma_regime > 0, "above_flip", "below_flip"), "unknown")
    if "btc_close" in data:
        btc_close = pd.to_numeric(data["btc_close"], errors="coerce")
        trend_ma = btc_close.rolling(20, min_periods=4).mean()
        trend = np.where(btc_close.notna() & trend_ma.notna(), np.where(btc_close >= trend_ma, 1.0, -1.0), 0.0)
        weight = weights.get("trend", 1.0)
        score += trend * weight
        total_weight += abs(weight)

    scale = total_weight * ZSCORE_CAP if total_weight else 1.0
    data["conviction"] = (score / scale * 100).clip(-100, 100)
    etf_mom = pd.to_numeric(data["etf_mom_4w"], errors="coerce") if "etf_mom_4w" in data else pd.Series(0, index=data.index)
    etf_net = pd.to_numeric(data["etf_net_1w"], errors="coerce") if "etf_net_1w" in data else pd.Series(0, index=data.index)
    btc_ret = pd.to_numeric(data["btc_ret_1w"], errors="coerce") if "btc_ret_1w" in data else pd.Series(0, index=data.index)
    data["flow_confirmation"] = (etf_mom > 0) & (btc_ret > 0)
    data["bearish_divergence"] = (etf_mom < 0) & (btc_ret > 0)
    # Historical flags must be causal too; latest display remains a descriptive snapshot.
    threshold = _expanding_quantile(etf_net, 0.1).fillna(np.inf)
    data["capitulation_contrarian"] = (etf_net < threshold) & (btc_ret < 0)
    if "gamma_regime" not in data:
        data["gamma_regime"] = "unknown"
    return data
