from __future__ import annotations

import pandas as pd

from etf_options.utils import upsert_csv


def test_upsert_preserves_options_across_runs(tmp_path):
    path = tmp_path / "weekly.csv"
    upsert_csv(pd.DataFrame([{"week_end": "2026-06-26", "opt_gex_net": 100.0, "etf_net_1w": 400.0}]), path)

    result = upsert_csv(pd.DataFrame([{"week_end": "2026-06-26", "opt_gex_net": float("nan"), "etf_net_1w": 450.0}]), path)

    row = result[result["week_end"] == "2026-06-26"].iloc[0]
    assert row["opt_gex_net"] == 100.0
    assert row["etf_net_1w"] == 450.0


def test_upsert_applies_revisions(tmp_path):
    path = tmp_path / "weekly.csv"
    upsert_csv(pd.DataFrame([{"week_end": "2026-06-26", "opt_gex_net": 100.0}]), path)

    result = upsert_csv(pd.DataFrame([{"week_end": "2026-06-26", "opt_gex_net": 200.0}]), path)

    assert result.iloc[0]["opt_gex_net"] == 200.0


def test_upsert_adds_new_weeks(tmp_path):
    path = tmp_path / "weekly.csv"
    upsert_csv(pd.DataFrame([{"week_end": "2026-06-26", "etf_net_1w": 1.0}]), path)

    result = upsert_csv(pd.DataFrame([{"week_end": "2026-07-03", "etf_net_1w": 2.0}]), path)

    assert result["week_end"].tolist() == ["2026-06-26", "2026-07-03"]


def test_upsert_first_write_no_existing(tmp_path):
    path = tmp_path / "weekly.csv"

    result = upsert_csv(pd.DataFrame([{"week_end": "2026-06-26", "etf_net_1w": 1.0}]), path)

    assert path.exists()
    assert result.iloc[0]["etf_net_1w"] == 1.0

