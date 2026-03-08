import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

// Chart source URLs for each indicator
const DATA_SOURCES: Record<string, { name: string; url?: string }> = {
  globalM2: { name: 'CoinGlass', url: 'https://www.coinglass.com/pro/i/bitcoin-m2-supply-growth' },
  financialConditions: { name: 'FRED', url: 'https://fred.stlouisfed.org/series/NFCI' },
  mvrvZScore: { name: 'Bitcoin Magazine Pro', url: 'https://www.bitcoinmagazinepro.com/charts/mvrv-zscore/' },
  realizedPrice: { name: 'Bitcoin Magazine Pro', url: 'https://www.bitcoinmagazinepro.com/charts/realized-price/' },
  twoHundredWeekMA: { name: 'Bitcoin Magazine Pro', url: 'https://www.bitcoinmagazinepro.com/charts/200-week-moving-average-heatmap/' },
  reserveRisk: { name: 'Bitcoin Magazine Pro', url: 'https://www.bitcoinmagazinepro.com/charts/reserve-risk/' },
  puellMultiple: { name: 'Bitcoin Magazine Pro', url: 'https://www.bitcoinmagazinepro.com/charts/puell-multiple/' },
  ahr999: { name: 'CoinGlass', url: 'https://www.coinglass.com/pro/i/ahr999' },
  hashRibbons: { name: 'CoinGlass', url: 'https://www.coinglass.com/pro/i/bitcoin-hash-ribbons-indicator' },
  sopr: { name: 'BGeometrics', url: 'https://charts.bgeometrics.com/sopr.html' },
  lthSupply: { name: 'Bitcoin Magazine Pro', url: 'https://www.bitcoinmagazinepro.com/charts/long-term-holder-supply/' },
  weeklyHigherLow: { name: 'TradingView', url: 'https://www.tradingview.com/chart/?symbol=COINBASE%3ABTCUSD' },
  stablecoinSupply: { name: 'DefiLlama', url: 'https://defillama.com/' },
  halvingCycle: { name: 'Calculated from next halving block height' },
};

interface Indicator {
  id: string;
  name: string;
  weight: number;
  description: string;
  bullishCondition: string;
  bearishCondition: string;
  neutralCondition?: string;
  whyItMatters: string;
  source: string;
}

interface Phase {
  title: string;
  subtitle: string;
  indicators: Indicator[];
}

const INDICATORS: Record<string, Phase> = {
  phase1: {
    title: "Phase 1: Macro Backdrop",
    subtitle: "Is the environment supportive?",
    indicators: [
    {
      id: "globalM2",
      name: "Global M2 Trend",
      weight: 1,
      description: "Tracks total money supply from 21 major central banks. BTC responds to M2 changes with a 60-90 day lag. Use the 12-week rate of change to determine trend.",
      bullishCondition: "12-week M2 change > +1% (expanding). Or YoY growth > +3%. BTC typically follows 60-90 days later.",
      bearishCondition: "12-week M2 change < -1% (contracting). Or YoY growth < 0%. Central banks actively tightening.",
      neutralCondition: "12-week M2 change between -1% and +1% (flat/transitioning).",
      whyItMatters: "BTC doesn't sustainably rally against tightening global liquidity. Every major bull run coincided with M2 expansion. This tells you if a buy CAN work. Note: Effect is lagged 60-90 days.",
      source: "BitcoinMagazinePro Global Liquidity, MacroMicro, or BGeometrics"
    },
    {
      id: "financialConditions",
      name: "Financial Conditions Index",
      weight: 1,
      description: "Chicago Fed NFCI measures stress in financial markets. Normalized to mean=0, std dev=1 since 1971. Weekly updates on FRED. This is a LEVEL indicator \u2014 no trend calculation needed.",
      bullishCondition: "NFCI < 0 (looser than average). Ideal: NFCI < -0.5 (very loose).",
      bearishCondition: "NFCI > +0.5 (tight conditions). Crisis-level: NFCI > +1.0 (March 2020 spiked to +0.7).",
      neutralCondition: "NFCI between 0 and +0.5 (tighter than average but not crisis).",
      whyItMatters: "Loosening financial conditions have preceded every major BTC bull run. Unlike M2 (money quantity), this measures credit access and risk appetite. Simple: negative = loose = bullish.",
      source: "FRED NFCI series (updated Wednesdays)"
    }]
  },
  phase2: {
    title: "Phase 2: Deep Value Zone",
    subtitle: "Is BTC historically cheap?",
    indicators: [
    { id: "mvrvZScore", name: "MVRV Z-Score", weight: 3, description: "Compares Bitcoin's market value to its realized value (aggregate cost basis), normalized by volatility. Identifies extreme over/undervaluation.", bullishCondition: "Below 0 (deep value). Ideal entry zone is below -0.5.", bearishCondition: "Above 3 (overheated). Cycle tops historically occur at 6-7+.", whyItMatters: "Near-perfect track record at identifying cycle bottoms. When MVRV Z-Score is in the green zone, buying has historically produced outsized returns.", source: "LookIntoBitcoin, Glassnode, CoinGlass" },
    { id: "realizedPrice", name: "Price vs Realized Price", weight: 3, description: "Realized Price is the average price at which all BTC last moved on-chain \u2014 the aggregate cost basis of all holders.", bullishCondition: "Price below Realized Price. Historically rare and excellent entry.", bearishCondition: "Price far above Realized Price. High MVRV ratio.", whyItMatters: "When price drops below realized price, the average holder is underwater. This has only happened at major cycle bottoms (2015, 2018, 2022).", source: "Glassnode, LookIntoBitcoin" },
    { id: "twoHundredWeekMA", name: "200-Week Moving Average", weight: 3, description: "The 200-week moving average smooths out all short-term noise to show Bitcoin's true long-term trend.", bullishCondition: "Price at or below 200W MA. Historically marks cycle bottoms.", bearishCondition: "Price extremely elevated above 200W MA (heatmap in red/orange zone).", whyItMatters: "BTC has spent very little time below this line in its history. Every touch of the 200W MA in bear markets has been a generational buying opportunity.", source: "BitcoinMagazinePro, TradingView" },
    { id: "reserveRisk", name: "Reserve Risk", weight: 2, description: "Measures the confidence of long-term holders relative to the price. High confidence + low price = low Reserve Risk = good time to buy.", bullishCondition: "Below 0.001 (green zone). HODLers are confident despite low prices.", bearishCondition: "Above 0.02 (red zone). Risk/reward unfavorable.", whyItMatters: "Captures when 'weak hands' are accumulating while price is depressed. Historically excellent at identifying asymmetric risk/reward setups.", source: "LookIntoBitcoin, Glassnode" },
    { id: "puellMultiple", name: "Puell Multiple", weight: 2, description: "Compares miner revenue today vs the 365-day average. Shows when miners are under stress (capitulating) or thriving.", bullishCondition: "Below 0.5 (green zone). Miners struggling \u2014 historically marks bottoms.", bearishCondition: "Above 4 (red zone). Miners highly profitable \u2014 often near tops.", whyItMatters: "Miner economics drive significant sell pressure. When the Puell Multiple is low, the worst of miner selling is typically over.", source: "LookIntoBitcoin, Glassnode" },
    { id: "ahr999", name: "Ahr999 Index", weight: 1, description: "Combines short-term cost basis with a geometric growth model to identify accumulation vs profit-taking zones.", bullishCondition: "Below 0.45 (dollar-cost-average zone). Below 1.2 is accumulation territory.", bearishCondition: "Above 1.2 (take profit zone).", whyItMatters: "Designed specifically to help long-term investors identify when to accumulate vs when to take profits based on valuation.", source: "LookIntoBitcoin" }]
  },
  phase3: {
    title: "Phase 3: Exhaustion",
    subtitle: "Have sellers run out of coins?",
    indicators: [
    { id: "hashRibbons", name: "Hash Ribbons", weight: 3, description: "Tracks when miners capitulate (30d MA crosses below 60d MA) and when they recover. 'Buy' signal fires when 30d crosses back above 60d.", bullishCondition: "Buy signal active \u2014 30d MA crossed back above 60d MA after capitulation.", bearishCondition: "Deep capitulation ongoing \u2014 30d MA falling further below 60d MA.", whyItMatters: "\"When miners give up, it's possibly the most powerful Bitcoin buy signal ever.\" Has caught every major cycle bottom. Your PRIMARY entry trigger.", source: "LookIntoBitcoin, Glassnode, Capriole" },
    { id: "sopr", name: "SOPR (7d MA)", weight: 2, description: "Spent Output Profit Ratio \u2014 measures whether coins moving on-chain are being sold at a profit (>1) or loss (<1).", bullishCondition: "Recovering above 1 after spending time below. Holders no longer selling at a loss.", bearishCondition: "Below 1 and falling. Capitulation ongoing.", whyItMatters: "When SOPR recovers above 1 after a bear market, it signals the worst of the selling is over. Confirms the turn that Hash Ribbons suggests.", source: "Glassnode, CryptoQuant" },
    { id: "lthSupply", name: "LTH Supply Trend", weight: 2, description: "Tracks coins held by Long-Term Holders (155+ days). Accumulation = LTH supply increasing. Distribution = decreasing.", bullishCondition: "Rate of change turning negative (distribution starting) \u2014 signals new capital absorbing LTH selling.", bearishCondition: "Aggressive accumulation while price falling (early bear) OR aggressive distribution at highs (late bull).", whyItMatters: "LTH distribution after accumulation signals fresh capital entering. This is healthy bull market behavior.", source: "Glassnode" }]
  },
  phase4: {
    title: "Phase 4: Confirmation",
    subtitle: "Does price structure agree?",
    indicators: [
    { id: "weeklyHigherLow", name: "Weekly Higher Low", weight: 1, description: "Basic price structure \u2014 are weekly candles making higher lows? This confirms the trend has actually changed.", bullishCondition: "3+ consecutive weekly higher lows established.", bearishCondition: "Still making lower lows. No trend reversal confirmed.", whyItMatters: "On-chain data can be early. This confirms the market is actually ACTING like a new bull regime before you add more size.", source: "Any charting platform (TradingView)" },
    { id: "stablecoinSupply", name: "Stablecoin Supply 90d \u0394", weight: 1, description: "Tracks 90-day change in total stablecoin supply (USDT, USDC, etc). Represents 'dry powder' on the sidelines.", bullishCondition: "Supply expanding after contraction. New capital entering crypto ecosystem.", bearishCondition: "Supply contracting. Capital leaving the ecosystem.", whyItMatters: "Stablecoins are the ammunition. When supply expands, there's fresh capital ready to deploy into BTC.", source: "DefiLlama (free API)" },
    { id: "halvingCycle", name: "Halving Cycle Position", weight: 2, description: "Where are we relative to the ~4-year halving cycle? Historically, best returns come 12-18 months post-halving.", bullishCondition: "Within 6-18 months post-halving. Supply shock taking effect.", bearishCondition: "Late cycle (24+ months post-halving) or pre-halving bear.", whyItMatters: "Every halving cuts new BTC supply in half. The 12-18 month window after halving has historically produced the strongest returns.", source: "Calculate from block height (April 2024 was last halving)" }]
  }
};

type Status = 'bullish' | 'neutral' | 'bearish';

const STATUS_CONFIG: Record<Status, {color: string;textColor: string;bgColor: string;label: string;value: number;}> = {
  bullish: { color: 'bg-emerald-500', textColor: 'text-emerald-400', bgColor: '#10b981', label: 'Bullish', value: 1 },
  neutral: { color: 'bg-amber-500', textColor: 'text-amber-400', bgColor: '#f59e0b', label: 'Neutral', value: 0 },
  bearish: { color: 'bg-red-500', textColor: 'text-red-400', bgColor: '#ef4444', label: 'Bearish', value: -1 }
};

const getRegimeSignal = (percentage: number) => {
  if (percentage >= 81) return { label: 'Deep Value', color: 'from-emerald-600 to-emerald-400', bgGlow: 'shadow-emerald-500/30', description: 'Max long, LFG!' };
  if (percentage >= 61) return { label: 'Accumulation Zone', color: 'from-emerald-600 to-amber-500', bgGlow: 'shadow-emerald-500/20', description: 'Attractive. Scale into position.' };
  if (percentage >= 41) return { label: 'Patience...', color: 'from-amber-600 to-amber-400', bgGlow: 'shadow-amber-500/20', description: 'So-so. Wait for more confirmation.' };
  if (percentage >= 21) return { label: 'Distribution Zone', color: 'from-amber-600 to-red-500', bgGlow: 'shadow-amber-500/20', description: 'Risky. Scale out of positions.' };
  return { label: 'Overheated', color: 'from-red-600 to-red-400', bgGlow: 'shadow-red-500/30', description: 'GTFO, baby!' };
};

const IndicatorCard = ({ indicator, status, expanded, onToggle }: {indicator: Indicator;status: Status;expanded: boolean;onToggle: () => void;}) => {
  const statusConfig = STATUS_CONFIG[status];
  const dataSource = DATA_SOURCES[indicator.id];

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden mb-2">
      <button onClick={onToggle} className="w-full p-4 flex items-center justify-between text-left min-h-[52px] active:bg-slate-700/30 transition-colors">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-100 text-sm truncate">{indicator.name}</span>
            </div>
            <span className={`text-sm ${statusConfig.textColor}`}>{statusConfig.label}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500 flex-shrink-0">{"\u00d7"}{indicator.weight}</span>
          <div className={`w-2.5 h-2.5 rounded-full ${statusConfig.color}`} />
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded &&
      <div className="px-4 pb-4 border-t border-slate-700/50">
          <div className="pt-3.5 space-y-3">
            <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg" style={{ background: `${statusConfig.bgColor}15` }}>
              <div className={`w-2 h-2 rounded-full ${statusConfig.color}`} />
              <span className={`text-sm font-semibold ${statusConfig.textColor}`}>Currently: {statusConfig.label}</span>
            </div>

            <p className="text-sm text-slate-400 leading-relaxed">{indicator.description}</p>

            <div className="space-y-2">
              <div className="flex items-start gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <div>
                  <span className="text-sm font-semibold text-emerald-400">Bullish when:</span>
                  <p className="text-sm text-slate-300 mt-0.5">{indicator.bullishCondition}</p>
                </div>
              </div>

              {indicator.neutralCondition &&
            <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <div>
                    <span className="text-sm font-semibold text-amber-400">Neutral when:</span>
                    <p className="text-sm text-slate-300 mt-0.5">{indicator.neutralCondition}</p>
                  </div>
                </div>
            }

              <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <div>
                  <span className="text-sm font-semibold text-red-400">Bearish when:</span>
                  <p className="text-sm text-slate-300 mt-0.5">{indicator.bearishCondition}</p>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-700/30 border border-slate-600/30">
              <p className="text-sm font-semibold text-blue-400 mb-1">Why This Matters</p>
              <p className="text-sm text-slate-300 leading-relaxed">{indicator.whyItMatters}</p>
            </div>

            <div className="flex items-center gap-2 text-sm text-slate-500">
              <span>Source: {dataSource?.url ? (
                <a href={dataSource.url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 underline underline-offset-2 transition-colors">{dataSource.name}</a>
              ) : (
                <span className="text-slate-400">{dataSource?.name}</span>
              )}</span>
            </div>
          </div>
        </div>
      }
    </div>);
};

const PhaseSection = ({ phase, phaseKey, indicators, expanded, onToggle, expandedIndicator, onIndicatorToggle }: {phase: Phase;phaseKey: string;indicators: Record<string, Status>;expanded: boolean;onToggle: () => void;expandedIndicator: string | null;onIndicatorToggle: (id: string) => void;}) => {
  const phaseIndicators = INDICATORS[phaseKey].indicators;
  const phaseScore = phaseIndicators.reduce((acc, ind) => {
    const status = indicators[ind.id] || 'neutral';
    return acc + STATUS_CONFIG[status].value * ind.weight;
  }, 0);
  const maxPhaseScore = phaseIndicators.reduce((acc, ind) => acc + ind.weight, 0);

  const getPhaseStatus = () => {
    if (phaseScore > maxPhaseScore * 0.3) return { color: 'text-emerald-400' };
    if (phaseScore < -maxPhaseScore * 0.3) return { color: 'text-red-400' };
    return { color: 'text-amber-400' };
  };

  const phaseStatus = getPhaseStatus();

  return (
    <div className="mb-4">
      <button
        onClick={onToggle}
        className="w-full p-4 bg-slate-800/80 rounded-xl border border-slate-700/50 flex items-center justify-between mb-2 min-h-[56px] active:bg-slate-700/60 transition-colors">
        <div className="flex items-center gap-3">
          <div className="text-left">
            <h3 className="font-bold text-slate-100 text-lg">{phase.title}</h3>
            <p className="text-slate-400 text-base mt-2">{phase.subtitle}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-mono font-bold ${phaseStatus.color}`}>
            {phaseScore > 0 ? '+' : ''}{phaseScore}/{maxPhaseScore}
          </span>
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded &&
      <div className="pl-2">
          {phaseIndicators.map((indicator) =>
        <IndicatorCard
          key={indicator.id}
          indicator={indicator}
          status={indicators[indicator.id] as Status || 'neutral'}
          expanded={expandedIndicator === indicator.id}
          onToggle={() => onIndicatorToggle(indicator.id)} />
        )}
        </div>
      }
    </div>);
};

export default function BTCRegimeTracker() {
  const [indicators, setIndicators] = useState<Record<string, Status>>({});
  const [expandedPhase, setExpandedPhase] = useState<string | null>(null);
  const [expandedIndicator, setExpandedIndicator] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [updatedBy, setUpdatedBy] = useState<string | null>(null);
  const [btcPrice, setBtcPrice] = useState<number | null>(null);

  // Load data from indicator-data.json
  useEffect(() => {
    const loadData = async () => {
      try {
        const res = await fetch(`${import.meta.env.BASE_URL}indicator-data.json`);
        if (res.ok) {
          const data = await res.json();
          if (data.indicators) setIndicators(data.indicators);
          if (data.lastUpdated) setLastUpdated(data.lastUpdated);
          if (data.updatedBy) setUpdatedBy(data.updatedBy);
        }
      } catch (e) {
        console.log('Data fetch error:', e);
      }
    };
    loadData();

    const fetchBtcPrice = async () => {
      try {
        const res = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd');
        if (res.ok) {
          const data = await res.json();
          setBtcPrice(data.bitcoin.usd);
        }
      } catch (e) {
        console.log('BTC price fetch error:', e);
      }
    };
    fetchBtcPrice();
    const priceInterval = setInterval(fetchBtcPrice, 60000);
    return () => clearInterval(priceInterval);
  }, []);

  const allIndicators = Object.values(INDICATORS).flatMap((phase) => phase.indicators);
  const rawScore = allIndicators.reduce((acc, ind) => {
    const status = indicators[ind.id] || 'neutral';
    return acc + STATUS_CONFIG[status].value * ind.weight;
  }, 0);
  const maxScore = allIndicators.reduce((acc, ind) => acc + ind.weight, 0);
  const percentage = Math.round((rawScore + maxScore) / (2 * maxScore) * 100);
  const regime = getRegimeSignal(percentage);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white max-w-md mx-auto">
      {/* Header */}
      <div className="border-b border-slate-800/50">
        <div className="px-4 py-3">
          <div>
            <h1 className="font-bold text-slate-100 tracking-tight mt-8 mb-1 text-3xl">Time to Buy Bitcoin?</h1>
            <p className="text-slate-500 text-lg">Generational Entries/Exits Checklist</p>
            {btcPrice !== null && (
              <p className="text-slate-300 text-xl font-mono font-semibold my-4">
                BTC: ${btcPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Main Signal */}
      <div className="p-4">
        <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${regime.color} p-6 shadow-2xl ${regime.bgGlow}`}>
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />
          <div className="relative text-center">
            <div className="text-5xl font-black mb-1 tracking-tighter" style={{ textShadow: '0 2px 4px rgba(0,0,0,0.3)' }}>
              {percentage}%
            </div>
             <div className="text-lg text-white/70 mb-3 font-mono">
              CONVICTION 
            </div>
            <div className="inline-block px-4 py-1.5 bg-black/30 rounded-full">
              <span className="font-bold tracking-wide text-sm">{regime.label}</span>
            </div>
            <p className="text-white/80 mt-3 max-w-xs mx-auto text-sm">{regime.description}</p>
          </div>
        </div>

        {lastUpdated &&
        <div className="text-center mt-3">
            <span className="text-xs text-slate-500">
              Updates weekly. Last update {new Date(lastUpdated).toLocaleDateString('en-US', {
              day: 'numeric', month: 'short'
            })}.
            </span>
          </div>
        }
      </div>

      {/* Score Thresholds */}
      <div className="px-4 mb-4">
        <div className="p-4 bg-slate-800/30 rounded-xl border border-slate-700/30">
          <h4 className="font-semibold text-slate-200 text-base mb-2.5">Conviction Tier</h4>
          <div className="text-sm text-slate-400 leading-relaxed">
            <table className="border-collapse table-auto w-auto">
              <tbody className="[&>tr]:align-top [&>tr:not(:last-child)]:border-0 [&>tr:not(:last-child)]:border-transparent [&>tr:not(:last-child)]:[&>td]:pb-1.5">
                {[
                  { range: '81-100%', label: 'Deep Value', colorClass: 'text-emerald-500', min: 81 },
                  { range: '61-80%', label: 'Accumulation Zone', colorClass: 'text-[#69c38a]', min: 61 },
                  { range: '41-60%', label: 'Patience...', colorClass: 'text-yellow-500', min: 41 },
                  { range: '21-40%', label: 'Distribution Zone', colorClass: 'text-orange-500', min: 21 },
                  { range: '0-20%', label: 'Overheated', colorClass: 'text-red-500', min: 0 },
                ].map((tier) => {
                  const isActive = regime.label === tier.label;
                  return (
                    <tr key={tier.range}>
                      <td className={`w-4 pr-2 ${tier.colorClass}`}>{"\u25a0"}</td>
                      <td className="text-slate-300 font-medium whitespace-nowrap">{tier.range}</td>
                      <td className="px-1">:</td>
                      <td>
                        {tier.label}
                        {isActive && <span className="text-slate-500 italic ml-1">— {regime.description}</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Phase Sections */}
      <div className="px-4 pb-24">
        {Object.entries(INDICATORS).map(([phaseKey, phase]) =>
        <PhaseSection
          key={phaseKey}
          phase={phase}
          phaseKey={phaseKey}
          indicators={indicators}
          expanded={expandedPhase === phaseKey}
          onToggle={() => setExpandedPhase(expandedPhase === phaseKey ? null : phaseKey)}
          expandedIndicator={expandedIndicator}
          onIndicatorToggle={(id) => setExpandedIndicator(expandedIndicator === id ? null : id)} />
        )}

        {/* How to Use Guide */}
        <details className="mt-6 bg-slate-800/30 rounded-xl border border-slate-700/30 group">
          <summary className="p-4 font-semibold text-slate-200 text-base cursor-pointer list-none flex items-center justify-between [&::-webkit-details-marker]:hidden">
            How to Use This
            <svg className="w-4 h-4 text-slate-400 transition-transform group-open:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
          </summary>
          <div className="px-4 pb-4 text-sm text-slate-400 space-y-3 leading-relaxed">
            <p><span className="text-slate-300 font-medium">Phase 1: Macro</span><br />Must be neutral or bullish to have permission to play.</p>
            <p><span className="text-slate-300 font-medium">Phase 2: Value</span><br />Tells you if BTC is cheap. Not always a buy signal yet.</p>
            <p><span className="text-slate-300 font-medium">Phase 3: Exhaustion</span><br />Your primary trigger, especially Hash Ribbons.</p>
            <p><span className="text-slate-300 font-medium">Phase 4: Confirmation</span><br />Additional signs that support size.</p>
          </div>
        </details>

        {/* Weight System */}
        <details className="mt-4 bg-slate-800/30 rounded-xl border border-slate-700/30 group">
          <summary className="p-4 font-semibold text-slate-200 text-base cursor-pointer list-none flex items-center justify-between [&::-webkit-details-marker]:hidden">
            Indicator Weights System
            <svg className="w-4 h-4 text-slate-400 transition-transform group-open:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
          </summary>
          <div className="px-4 pb-4 text-sm text-slate-400 leading-relaxed space-y-1.5">
            <p className="mb-4">Some indicators are more important than others. The higher the weight the more useful.</p>
            <p><span className="text-slate-300 font-medium">{"\u00d7"}3: Near perfect track record</span><br />MVRV Z-Score, Hash Ribbons, 200-Week MA, Realized Price</p>
            <p><span className="text-slate-300 font-medium">{"\u00d7"}2: Excellent but sometimes early</span><br />Puell, Reserve Risk, LTH Supply, SOPR, Halving</p>
            <p><span className="text-slate-300 font-medium">{"\u00d7"}1: Useful confirmation</span><br />Macro indicators, stablecoins, price structure</p>
          </div>
        </details>

        <p className="mt-8 text-xs text-slate-500 italic text-center">Backtested, but not rigorously. Not financial advice.</p>
      </div>
    </div>);
}
