from __future__ import annotations

import json
from pathlib import Path

from etf_options import sources_options
from etf_options.sources_options import fetch_dvol, parse_instrument, snapshot_options

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_parse_instrument():
    parsed = parse_instrument("BTC-27JUN25-60000-C")

    assert parsed["strike"] == 60000.0
    assert parsed["type"] == "C"
    assert parsed["expiry"].tzinfo is not None


def test_snapshot_options_maps_greeks_and_skips_malformed(monkeypatch, caplog):
    summaries = json.loads((FIXTURES / "deribit_book_summary.json").read_text())
    instruments = json.loads((FIXTURES / "deribit_instruments.json").read_text())

    def fake_get(method, params=None):
        if method == "get_book_summary_by_currency":
            return summaries
        if method == "get_instruments":
            return instruments
        if method == "ticker":
            return {
                "mark_iv": 60.0,
                "mark_price": 0.09,
                "underlying_price": 60000,
                "greeks": {"delta": -0.30, "gamma": 0.00003, "vega": 31.0},
            }
        raise AssertionError(method)

    monkeypatch.setattr(sources_options, "_get", fake_get)

    chain = snapshot_options(ticker_limit=10)

    assert "BTC-PERPETUAL" not in set(chain["instrument"])
    assert any("Skipping malformed" in record.message for record in caplog.records)
    call = chain[chain["instrument"] == "BTC-27JUN25-60000-C"].iloc[0]
    put = chain[chain["instrument"] == "BTC-27JUN25-55000-P"].iloc[0]
    assert call["oi"] == 10
    assert call["gamma"] == 0.00002
    assert put["mark_iv"] == 60.0
    assert put["gamma"] == 0.00003


def test_fetch_dvol_uses_latest_close(monkeypatch):
    def fake_get(method, params=None):
        assert method == "get_volatility_index_data"
        return {"data": [[1, 40.0, 45.0, 39.0, 44.0], [2, 50.0, 56.0, 49.0, 55.5]]}

    monkeypatch.setattr(sources_options, "_get", fake_get)

    assert fetch_dvol() == 55.5
