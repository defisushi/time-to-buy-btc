# time-to-buy-btc

BTC conviction score tracker. Frontend displays 14 on-chain/macro indicators as bullish/neutral/bearish signals, plus a second ETF flows/options positioning page.

## Stack
- React + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- Hosted on GitHub Pages

## Key files
- `src/components/BTCRegimeTracker.tsx` — main frontend component
- `src/components/etf-options/ETFOptionsTracker.tsx` — ETF flows/options positioning page
- `public/indicator-data.json` — indicator data read by the frontend
- `public/etf-options-data.json` — precomputed ETF/options payload read by the frontend
- `scripts/fetch_indicators.py` — fetches all 14 indicators and writes indicator-data.json
- `scripts/etf_options/fetch_etf_options.py` — fetches ETF flows, Deribit options, BTC price, weekly archive, and writes etf-options-data.json
- `data/etf_options_weekly.csv` — committed weekly ETF/options archive
- `data/options_snapshot_latest.json` — latest full option-chain snapshot for strike charts
- `.github/workflows/update_conviction.yml` — runs fetch_indicators.py every Friday 1am UTC, then triggers deploy
- `.github/workflows/deploy.yml` — builds and deploys to GitHub Pages

## Indicators
3 fetched directly (no API key): weeklyHigherLow (CoinGecko), stablecoinSupply (DefiLlama), halvingCycle (date math)
11 fetched via Grok web search: globalM2, financialConditions, mvrvZScore, realizedPrice, twoHundredWeekMA, reserveRisk, puellMultiple, ahr999, hashRibbons, sopr, lthSupply

ETF/options page data is keyless: Farside Investors for spot BTC ETF flows, Binance/CoinGecko for BTC price, and Deribit public REST for BTC option-chain snapshots. ETF flows and price are back-fillable; option-chain history starts accumulating from the first successful weekly run.

## Secrets
- `GROK_API_KEY` — stored in GitHub repo secrets (xAI console)

## Deploy
Push to main triggers a deploy. The weekly indicator update also triggers a deploy automatically.
To push: `git push origin main` (auth via gh CLI — run `gh auth login` if needed)
