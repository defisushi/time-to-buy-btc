from __future__ import annotations

from pathlib import Path

import pytest

from etf_options import sources_etf
from etf_options.sources_etf import clean_flow, fetch_etf_flows, load_etf_flows_from_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class Response:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_clean_flow():
    assert clean_flow("(123.4)") == -123.4
    assert clean_flow("-") is None
    assert clean_flow("$1,234.5") == 1234.5
    assert clean_flow("1,000") == 1000.0
    assert clean_flow("") is None
    assert clean_flow("nan") is None


def test_fetch_etf_flows_long_form_and_sign(monkeypatch):
    html = (FIXTURES / "farside_sample.html").read_text()
    monkeypatch.setattr(sources_etf.requests, "get", lambda *args, **kwargs: Response(html))

    flows = fetch_etf_flows()

    ibit = flows[(flows["event_date"].dt.date.astype(str) == "2024-01-12") & (flows["ticker"] == "IBIT")].iloc[0]
    assert ibit["net_flow_usd_m"] == -123.4
    assert set(["event_date", "ticker", "net_flow_usd_m", "avail_date", "source"]).issubset(flows.columns)


def test_avail_date_friday_to_monday(monkeypatch):
    html = (FIXTURES / "farside_sample.html").read_text()
    monkeypatch.setattr(sources_etf.requests, "get", lambda *args, **kwargs: Response(html))

    flows = fetch_etf_flows()

    total = flows[(flows["event_date"].dt.date.astype(str) == "2024-01-12") & (flows["ticker"] == "TOTAL")].iloc[0]
    assert total["avail_date"].date().isoformat() == "2024-01-15"


def test_missing_total_raises(monkeypatch):
    html = """
    <table><thead><tr><th>Date</th><th>IBIT</th><th>FBTC</th><th>ARKB</th></tr></thead>
    <tbody><tr><td>2024-01-12</td><td>1</td><td>2</td><td>3</td></tr></tbody></table>
    """
    monkeypatch.setattr(sources_etf.requests, "get", lambda *args, **kwargs: Response(html))

    with pytest.raises(RuntimeError):
        fetch_etf_flows()


def test_load_etf_flows_from_html_file():
    flows = load_etf_flows_from_file(FIXTURES / "farside_sample.html")

    ibit = flows[(flows["event_date"].dt.date.astype(str) == "2024-01-12") & (flows["ticker"] == "IBIT")].iloc[0]
    assert set(["event_date", "ticker", "net_flow_usd_m", "avail_date", "source"]).issubset(flows.columns)
    assert ibit["net_flow_usd_m"] == -123.4
    assert ibit["avail_date"].date().isoformat() == "2024-01-15"
    assert ibit["source"] == "Farside Investors (manual)"


def test_load_etf_flows_from_csv_file():
    flows = load_etf_flows_from_file(FIXTURES / "farside_sample.csv")

    total = flows[(flows["event_date"].dt.date.astype(str) == "2024-01-12") & (flows["ticker"] == "TOTAL")].iloc[0]
    assert total["net_flow_usd_m"] == 1000.0
    assert total["avail_date"].date().isoformat() == "2024-01-15"
    assert total["source"] == "Farside Investors (manual)"
