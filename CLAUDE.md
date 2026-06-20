# time-to-buy-btc

BTC conviction score tracker. Frontend displays 14 on-chain/macro indicators as bullish/neutral/bearish signals.

## Stack
- React + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- Hosted on GitHub Pages

## Key files
- `src/components/BTCRegimeTracker.tsx` — main frontend component
- `public/indicator-data.json` — indicator data read by the frontend
- `scripts/fetch_indicators.py` — fetches all 14 indicators and writes indicator-data.json
- `.github/workflows/update_conviction.yml` — runs fetch_indicators.py every Friday 1am UTC, then triggers deploy
- `.github/workflows/deploy.yml` — builds and deploys to GitHub Pages

## Indicators
3 fetched directly (no API key): weeklyHigherLow (CoinGecko), stablecoinSupply (DefiLlama), halvingCycle (date math)
11 fetched via Grok web search: globalM2, financialConditions, mvrvZScore, realizedPrice, twoHundredWeekMA, reserveRisk, puellMultiple, ahr999, hashRibbons, sopr, lthSupply

## Secrets
- `GROK_API_KEY` — stored in GitHub repo secrets (xAI console)

## Deploy
Push to main triggers a deploy. The weekly indicator update also triggers a deploy automatically.
To push: `git push origin main` (auth via gh CLI — run `gh auth login` if needed)
