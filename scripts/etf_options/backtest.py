"""Walk-forward backtest helpers for the ETF/options signal."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _source_dates(data: pd.DataFrame, signal_col: str) -> pd.Series:
    source_col = f"{signal_col}_source_week_end"
    if source_col in data.columns:
        return pd.to_datetime(data[source_col], utc=True)
    return data["week_end_dt"]


def walk_forward(weekly: pd.DataFrame, signal_col: str, cost_bps: float = 10) -> dict[str, Any]:
    """Backtest a weekly signal with publication-date alignment and transaction costs."""
    required = {"week_end", "avail_date_etf", "btc_ret_1w", signal_col}
    missing = required.difference(weekly.columns)
    if missing:
        return {"equity": [], "sharpe": None, "max_dd": None, "hit_rate": None, "turnover": None, "vs_hodl": None, "error": f"missing {sorted(missing)}"}

    data = weekly.copy()
    data["week_end_dt"] = pd.to_datetime(data["week_end"], utc=True)
    data["avail_date_dt"] = pd.to_datetime(data["avail_date_etf"], utc=True)
    if (data["avail_date_dt"] < data["week_end_dt"]).any():
        raise AssertionError("ETF flow availability predates event week end; look-ahead risk")

    data = data.sort_values("week_end_dt").reset_index(drop=True)
    data["signal_source_week_end_dt"] = _source_dates(data, signal_col)
    if (data["signal_source_week_end_dt"] > data["week_end_dt"]).any():
        raise AssertionError("Signal source week is in the future")

    signal = pd.to_numeric(data[signal_col], errors="coerce").fillna(0)
    returns = pd.to_numeric(data["btc_ret_1w"], errors="coerce").fillna(0)
    return_starts = data["week_end_dt"].shift(1)
    position = pd.Series(0.0, index=data.index)

    for row_idx, return_start in return_starts.items():
        if pd.isna(return_start):
            continue
        eligible = data.index[data["avail_date_dt"] <= return_start]
        if len(eligible) == 0:
            continue
        chosen = int(eligible[-1])
        if return_start < data.loc[chosen, "avail_date_dt"]:
            raise AssertionError("Trade return window starts before signal availability")
        position.loc[row_idx] = 1.0 if signal.loc[chosen] > 0 else 0.0

    turnover = position.diff().abs().fillna(position.abs())
    strategy_ret = position * returns - turnover * (cost_bps / 10_000)
    hodl_ret = returns
    equity = (1 + strategy_ret).cumprod()
    hodl = (1 + hodl_ret).cumprod()
    drawdown = equity / equity.cummax() - 1

    rows = [
        {"week_end": row["week_end"], "strategy": float(equity.iloc[idx]), "hodl": float(hodl.iloc[idx])}
        for idx, row in data.iterrows()
    ]
    std = strategy_ret.std()
    sharpe = float(strategy_ret.mean() / std * np.sqrt(52)) if std and not np.isnan(std) else None
    hit_rate = float((np.sign(strategy_ret) == np.sign(hodl_ret)).mean()) if len(data) else None
    return {
        "equity": rows,
        "sharpe": sharpe,
        "max_dd": float(drawdown.min()) if len(drawdown) else None,
        "hit_rate": hit_rate,
        "turnover": float(turnover.mean()) if len(turnover) else None,
        "vs_hodl": float(equity.iloc[-1] - hodl.iloc[-1]) if len(equity) else None,
    }
