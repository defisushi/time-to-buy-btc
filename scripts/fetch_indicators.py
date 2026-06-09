#!/usr/bin/env python3
"""
BTC Conviction Score - Weekly Indicator Fetcher
================================================
Outputs: public/indicator-data.json
 
Schema matches BTCRegimeTracker.tsx exactly:
{
  "lastUpdated": "...",
  "updatedBy": "automated",
  "indicators": {
    "globalM2": "bullish" | "neutral" | "bearish",
    ...
  }
}
 
API keys required:
  GROK_API_KEY  — xAI console (console.x.ai)
 
No other API keys needed:
  CoinGecko  — free, no key
  DefiLlama  — free, no key
  Halving    — date math
"""
 
import os
import json
import requests
from datetime import datetime, timezone
from statistics import mean
 
GROK_API_KEY  = os.environ["GROK_API_KEY"]
 
COINGECKO_URL = "https://api.coingecko.com/api/v3"
DEFILLAMA_URL = "https://stablecoins.llama.fi"
GROK_API_URL  = "https://api.x.ai/v1/chat/completions"
 
Signal = str  # "bullish" | "neutral" | "bearish"
 
 
# ── Direct fetchers ──────────────────────────────────────────────────────────
 
def fetch_twoHundredWeekMA() -> Signal:
    """
    BTC price vs 200-week MA via CoinGecko weekly data.
    Bullish  = at or below MA
    Neutral  = up to 20% above MA
    Bearish  = > 20% above MA
    """
    resp = requests.get(
        f"{COINGECKO_URL}/coins/bitcoin/market_chart",
        params={"vs_currency": "usd", "days": "1400", "interval": "weekly"},
        timeout=30,
    )
    resp.raise_for_status()
    prices = [p[1] for p in resp.json()["prices"]]
    if len(prices) < 200:
        return "neutral"
    ma = mean(prices[-200:])
    pct_above = (prices[-1] - ma) / ma * 100
    if pct_above <= 0:
        return "bullish"
    if pct_above < 20:
        return "neutral"
    return "bearish"
 
 
def fetch_weeklyHigherLow() -> Signal:
    """
    Last 3 weekly lows from CoinGecko OHLC.
    Bullish  = each low higher than the last (higher lows confirmed)
    Bearish  = each low lower than the last (lower lows confirmed)
    Neutral  = mixed structure
    """
    resp = requests.get(
        f"{COINGECKO_URL}/coins/bitcoin/ohlc",
        params={"vs_currency": "usd", "days": "30"},
        timeout=20,
    )
    resp.raise_for_status()
    candles = resp.json()
    if len(candles) < 3:
        return "neutral"
    lows = [c[3] for c in candles[-3:]]
    if lows[2] > lows[1] > lows[0]:
        return "bullish"
    if lows[2] < lows[1] < lows[0]:
        return "bearish"
    return "neutral"
 
 
def fetch_stablecoinSupply() -> Signal:
    """
    Stablecoin supply 30d change via DefiLlama.
    Bullish  = > +3% growth
    Neutral  = 0 to +3%
    Bearish  = negative
    """
    resp = requests.get(f"{DEFILLAMA_URL}/stablecoins?includePrices=true", timeout=20)
    resp.raise_for_status()
    assets = resp.json().get("peggedAssets", [])
 
    now  = sum(float(s.get("circulating", {}).get("peggedUSD", 0) or 0) for s in assets)
    prev = sum(float(s.get("circulatingPrevMonth", {}).get("peggedUSD", 0) or 0) for s in assets)
 
    if prev == 0:
        return "neutral"
    pct = (now - prev) / prev * 100
    if pct > 3:
        return "bullish"
    if pct >= 0:
        return "neutral"
    return "bearish"
 
 
def fetch_halvingCycle() -> Signal:
    """
    Months since April 19 2024 halving.
    Bullish  = 6-18 months (supply shock window)
    Neutral  = 0-6 months (too early) or 18-30 months (late cycle, fading)
    Bearish  = 30+ months (deep late cycle)
    """
    last_halving = datetime(2024, 4, 19, tzinfo=timezone.utc)
    months = (datetime.now(timezone.utc) - last_halving).days / 30.44
    if 6 <= months <= 18:
        return "bullish"
    if months < 6 or (18 < months <= 30):
        return "neutral"
    return "bearish"
 
 
# ── Grok fetcher ─────────────────────────────────────────────────────────────
 
GROK_SYSTEM = """You are a data extraction assistant. Your ONLY job is to return a JSON object.
 
RULES:
1. Return ONLY valid JSON. No explanation, no markdown, no backticks.
2. Each value must be exactly one of: "bullish", "neutral", "bearish"
3. If you cannot find a confident reading within the last 2 weeks, return "neutral"
4. NEVER fabricate. Base signals on actual recent data from X/Twitter analysts,
   Glassnode, LookIntoBitcoin, CryptoQuant, FRED, Chicago Fed, macro sources, etc.
"""
 
GROK_USER = f"""Today is {datetime.now(timezone.utc).strftime("%Y-%m-%d")}.
 
Search for the most recent readings and classify each indicator as bullish, neutral, or bearish.
 
Use these exact thresholds:
 
globalM2:           bullish = 12-week M2 change > +1% (expanding) | neutral = -1% to +1% | bearish = < -1% (contracting)
financialConditions: bullish = NFCI < 0 (loose) | neutral = 0 to +0.5 | bearish = > +0.5 (tight)
mvrvZScore:         bullish = below 0.5 | neutral = 0.5-2.5 | bearish = above 2.5
realizedPrice:      bullish = price below or <10% above realized price | neutral = 10-50% above | bearish = >50% above
reserveRisk:        bullish = below 0.001 | neutral = 0.001-0.02 | bearish = above 0.02
puellMultiple:      bullish = below 0.5 | neutral = 0.5-1.5 | bearish = above 1.5
ahr999:             bullish = below 0.45 | neutral = 0.45-1.2 | bearish = above 1.2
hashRibbons:        bullish = buy signal (30d crossed above 60d after capitulation) | neutral = no signal | bearish = capitulation ongoing (30d falling below 60d)
sopr:               bullish = 7d MA recovering above 1 | neutral = hovering near 1 | bearish = below 1 and falling
lthSupply:          bullish = LTH supply increasing (accumulation) | neutral = flat | bearish = LTH supply decreasing (distribution)
 
Return this exact JSON structure:
{{
  "globalM2": "...",
  "financialConditions": "...",
  "mvrvZScore": "...",
  "realizedPrice": "...",
  "reserveRisk": "...",
  "puellMultiple": "...",
  "ahr999": "...",
  "hashRibbons": "...",
  "sopr": "...",
  "lthSupply": "..."
}}"""
 
 
def fetch_grok_indicators() -> dict[str, Signal]:
    resp = requests.post(
        GROK_API_URL,
        headers={
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type":  "application/json",
        },
        json={
            "model":       "grok-3",
            "messages": [
                {"role": "system", "content": GROK_SYSTEM},
                {"role": "user",   "content": GROK_USER},
            ],
            "max_tokens":  300,
            "temperature": 0,
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
 
    # Strip markdown fences if Grok wraps response
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()
 
    raw = json.loads(content)
 
    # Validate — only accept known signal values, default unknown to neutral
    valid = {"bullish", "neutral", "bearish"}
    grok_keys = [
        "globalM2", "financialConditions", "mvrvZScore", "realizedPrice",
        "reserveRisk", "puellMultiple", "ahr999", "hashRibbons", "sopr", "lthSupply"
    ]
    return {k: raw[k] if raw.get(k) in valid else "neutral" for k in grok_keys}
 
 
# ── Main ─────────────────────────────────────────────────────────────────────
 
def run():
    now = datetime.now(timezone.utc).isoformat()
    print(f"[{now}] Fetching indicators...")
 
    indicators: dict[str, Signal] = {}
 
    # Direct fetchers — no API key needed
    direct = {
        "twoHundredWeekMA": fetch_twoHundredWeekMA,
        "weeklyHigherLow":  fetch_weeklyHigherLow,
        "stablecoinSupply": fetch_stablecoinSupply,
        "halvingCycle":     fetch_halvingCycle,
    }
 
    for key, fn in direct.items():
        try:
            result = fn()
            indicators[key] = result
            print(f"  ✓ {key}: {result}")
        except Exception as e:
            print(f"  ✗ {key}: FAILED ({e}) → neutral")
            indicators[key] = "neutral"
 
    # Grok — single call for all 10 remaining indicators
    print("  Querying Grok...")
    try:
        grok = fetch_grok_indicators()
        indicators.update(grok)
        for k, v in grok.items():
            print(f"  ✓ {k}: {v} (grok)")
    except Exception as e:
        print(f"  ✗ Grok FAILED ({e}) → all neutral")
        for key in ["globalM2", "financialConditions", "mvrvZScore", "realizedPrice",
                    "reserveRisk", "puellMultiple", "ahr999", "hashRibbons", "sopr", "lthSupply"]:
            indicators[key] = "neutral"
 
    # Write output matching indicator-data.json schema exactly
    output = {
        "lastUpdated": now,
        "updatedBy":   "automated",
        "indicators":  indicators,
    }
 
    out_path = os.path.join(os.path.dirname(__file__), "..", "public", "indicator-data.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
 
    print(f"\n  Wrote public/indicator-data.json")
    print(f"  Indicators: {indicators}")
 
 
if __name__ == "__main__":
    run()
 
