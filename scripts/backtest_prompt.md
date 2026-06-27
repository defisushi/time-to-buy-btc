# Backtest Prompt for Codex

I want to build a backtest to empirically split the "Mid-Cycle" zone (31–84%) of my Bitcoin conviction score model into more meaningful sub-zones. Before writing any code, read these files in the repo to fully understand the methodology:

- `src/components/BTCRegimeTracker.tsx` — all 14 indicators, their weights, bullish/neutral/bearish thresholds, and the exact scoring formula
- `scripts/fetch_indicators.py` — how each indicator is fetched and classified weekly
- `public/indicator-data.json` — sample output showing current indicator readings
- `CLAUDE.md` — project overview

---

## Background: The Full Model

The live model scores 14 indicators, each classified as bullish (+1), neutral (0), or bearish (-1), multiplied by a weight. The scoring formula is:

```
percentage = (rawScore + maxScore) / (2 * maxScore) * 100
```

This maps the full range to 0–100%, where 50% = all neutral, 100% = all bullish, 0% = all bearish.

**Total max score across all 14 indicators = 27**

**Historically validated tier boundaries (do not change these):**
- 85–100% = Generational Bottoms — all 5 historical cycle bottoms scored here (Nov 2011, Jan 2015, Dec 2018, Mar 2020, Nov 2022)
- 0–30% = Historical Tops — all 5 cycle tops scored here (Jun 2011, Nov 2013, Dec 2017, Nov 2021, Oct 2025)
- 31–84% = Mid-Cycle No Signal — empirically unvalidated, this is what we want to split

---

## The Backtest Goal

Calculate weekly conviction scores historically using only the indicators reconstructable from free data, then measure forward BTC returns at 3, 6, and 12 month horizons for each score reading. Find where within the 31–84% range the return profile shifts — those inflection points become new empirical tier boundaries.

---

## Data Source: coinmetrics/data GitHub repo

Use the free bulk CSV from: `https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv`

This is a single downloadable CSV, no API key required, no rate limits, updated daily, covering Bitcoin from genesis to present. Download it once at the start of the script and work from it locally.

**Relevant columns available in this CSV:**
- `time` — date (YYYY-MM-DD)
- `PriceUSD` — daily BTC price in USD
- `CapMVRVCur` — MVRV ratio (Market Cap / Realized Cap). Note: this is the ratio, not the Z-Score. The Z-Score normalises by standard deviation — derive it from the ratio using a rolling mean and std dev over the full history
- `IssTotUSD` — total miner issuance in USD per day — use this to derive Puell Multiple (today's issuance / 365-day rolling average)
- `HashRate` — daily hash rate — use 30-day and 60-day MAs to approximate hash ribbons signal

**Also use:**
- DefiLlama `/stablecoinchart/all` endpoint for stablecoin supply history (already used in `fetch_indicators.py`) — free, no key, full history
- Date math for halving cycle position (hardcode halving dates: Nov 28 2012, Jul 9 2016, May 11 2020, Apr 19 2024)

---

## Indicators to Reconstruct and Their Exact Thresholds

Use the exact same weights and thresholds as defined in `BTCRegimeTracker.tsx`. Only reconstruct indicators where the source data is directly available — do not approximate indicators that require Glassnode-specific data (like LTH Supply, Reserve Risk, SOPR, AHR999, or Realized Price as a standalone metric).

**Reconstruct these 5 indicators:**

**1. twoHundredWeekMA** — weight 3
- Calculate the 200-week rolling average of `PriceUSD`
- Bullish: price at or below 200W MA
- Neutral: price up to 20% above 200W MA
- Bearish: price more than 20% above 200W MA

**2. mvrvZScore** — weight 3
- Derive from `CapMVRVCur`: compute rolling mean and rolling std dev of the MVRV ratio over the full available history, then Z-Score = (current - mean) / std
- Bullish: Z-Score below 0.5
- Neutral: Z-Score between 0.5 and 2.5
- Bearish: Z-Score above 2.5

**3. puellMultiple** — weight 2
- Derive from `IssTotUSD`: Puell Multiple = today's `IssTotUSD` / 365-day rolling average of `IssTotUSD`
- Bullish: below 0.5
- Neutral: 0.5 to 1.5
- Bearish: above 1.5 (note: historical tops saw 6–10x but code threshold is 1.5 — use the code threshold)

**4. stablecoinSupply** — weight 1
- Pull from DefiLlama `/stablecoinchart/all`, compute 90-day percentage change in total stablecoin supply
- Bullish: >+3% over 90 days
- Neutral: 0% to +3%
- Bearish: negative

**5. halvingCycle** — weight 2
- Hardcode halving dates: Nov 28 2012, Jul 9 2016, May 11 2020, Apr 19 2024
- For each date, calculate months since the most recent halving
- Bullish: 6–18 months post-halving
- Neutral: 0–6 months or 18–30 months post-halving
- Bearish: 30+ months post-halving

**Total max score for partial model = 3 + 3 + 2 + 1 + 2 = 11**

---

## Scoring Formula for the Partial Model

Apply the exact same formula as the full model but using only the partial max score:

```python
partial_percentage = (raw_partial_score + max_partial_score) / (2 * max_partial_score) * 100
```

**Important:** the partial score's 0–100% range will not map identically to the full model's 0–100%. Do not compare partial scores directly to the full model's tier boundaries (85%, 30%). The partial score is used solely to find internal inflection points within the mid-cycle range. Make this limitation prominent in the script output and comments.

---

## Backtest Methodology

1. Build a weekly time series (use Fridays, or end of each ISO week) from the earliest date where all 5 indicators have valid data — likely around 2015 once the 200W MA has enough history and stablecoin data exists
2. For each weekly data point, calculate:
   - Each indicator's signal (bullish/neutral/bearish) and weighted score
   - The partial conviction percentage
   - Forward BTC price returns at exactly 13 weeks (3 months), 26 weeks (6 months), and 52 weeks (12 months)
3. Exclude the most recent 52 weeks from the dataset since we can't compute 12-month forward returns yet
4. Group all weekly observations into 5-percentage-point buckets across the full 0–100% partial score range
5. For each bucket compute:
   - Number of observations (sample count)
   - Mean and median forward return at 3m, 6m, 12m
   - % of observations with positive 12m return
6. Output a clean table sorted by score bucket

---

## Output Requirements

The script should print:

1. **Data summary:** date range used, total weekly observations, which indicators were successfully reconstructed
2. **Main results table:** score bucket | count | mean 3m return | median 3m return | mean 6m return | median 6m return | mean 12m return | median 12m return | % positive 12m
3. **Inflection point analysis:** identify where in the partial score range the median 12m return crosses from positive to negative and vice versa — flag these as candidate tier boundaries
4. **Prominent disclaimer** that this is a partial model using 5 of 14 indicators, the missing 9 are the ones requiring paid on-chain data, and the partial scores are not directly comparable to the full model's tier boundaries

---

## Code Requirements

- Self-contained Python script, no API keys required
- Save the coinmetrics CSV locally on first run and reuse it (don't re-download every run)
- Handle missing data gracefully — if a row has NaN for any indicator, skip that week
- Use only standard libraries plus `pandas`, `numpy`, and `requests`
- Put the script in `scripts/backtest_midcycle.py` to fit the existing repo structure
- Add clear section comments explaining each step
- Print runtime and data freshness at the end
