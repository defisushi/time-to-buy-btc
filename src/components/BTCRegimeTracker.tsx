import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Info, CheckCircle, AlertCircle, Clock, DollarSign, Activity, Zap, BarChart3, Layers, Calendar, Wallet, TrendingUp } from 'lucide-react';

interface Indicator {
  id: string;
  name: string;
  weight: number;
  icon: React.ElementType;
  description: string;
  bullishCondition: string;
  bearishCondition: string;
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
    subtitle: "Permission to play — is the environment supportive?",
    indicators: [
      {
        id: "globalM2",
        name: "Global M2 Trend",
        weight: 1,
        icon: DollarSign,
        description: "Tracks the total money supply from major central banks (Fed, ECB, BOJ, PBOC). Bitcoin correlates strongly with global liquidity cycles.",
        bullishCondition: "90-day rate of change is positive or stabilizing. M2 growing 3-5% YoY.",
        bearishCondition: "M2 actively contracting. Central banks tightening aggressively.",
        whyItMatters: "BTC doesn't sustainably rally against tightening global liquidity. Every major bull run coincided with M2 expansion. This tells you if a buy CAN work.",
        source: "FRED (M2SL series) or MacroMicro"
      },
      {
        id: "financialConditions",
        name: "Financial Conditions Index",
        weight: 1,
        icon: Activity,
        description: "The NFCI measures stress in financial markets — credit availability, risk appetite, and overall financial system health.",
        bullishCondition: "NFCI below 0 (loosening conditions). Fed cutting rates.",
        bearishCondition: "NFCI rising above 0 (tightening). Credit stress increasing.",
        whyItMatters: "Loosening financial conditions have preceded every major BTC bull run. This complements M2 by measuring credit access, not just money quantity.",
        source: "FRED (NFCI series)"
      }
    ]
  },
  phase2: {
    title: "Phase 2: Deep Value Zone",
    subtitle: "Is BTC historically cheap? (Necessary but not sufficient)",
    indicators: [
      { id: "mvrvZScore", name: "MVRV Z-Score", weight: 3, icon: BarChart3, description: "Compares Bitcoin's market value to its realized value (aggregate cost basis), normalized by volatility. Identifies extreme over/undervaluation.", bullishCondition: "Below 0 (deep value). Ideal entry zone is below -0.5.", bearishCondition: "Above 3 (overheated). Cycle tops historically occur at 6-7+.", whyItMatters: "Near-perfect track record at identifying cycle bottoms. When MVRV Z-Score is in the green zone, buying has historically produced outsized returns.", source: "LookIntoBitcoin, Glassnode, CoinGlass" },
      { id: "realizedPrice", name: "Price vs Realized Price", weight: 3, icon: Layers, description: "Realized Price is the average price at which all BTC last moved on-chain — the aggregate cost basis of all holders.", bullishCondition: "Price below Realized Price (~$56-58K currently). Historically rare and excellent entry.", bearishCondition: "Price far above Realized Price. High MVRV ratio.", whyItMatters: "When price drops below realized price, the average holder is underwater. This has only happened at major cycle bottoms (2015, 2018, 2022).", source: "Glassnode, LookIntoBitcoin" },
      { id: "twoHundredWeekMA", name: "200-Week Moving Average", weight: 3, icon: TrendingUp, description: "The 200-week moving average smooths out all short-term noise to show Bitcoin's true long-term trend.", bullishCondition: "Price at or below 200W MA (~$58K currently). Historically marks cycle bottoms.", bearishCondition: "Price extremely elevated above 200W MA (heatmap in red/orange zone).", whyItMatters: "BTC has spent very little time below this line in its history. Every touch of the 200W MA in bear markets has been a generational buying opportunity.", source: "BitcoinMagazinePro, TradingView" },
      { id: "reserveRisk", name: "Reserve Risk", weight: 2, icon: Wallet, description: "Measures the confidence of long-term holders relative to the price. High confidence + low price = low Reserve Risk = good time to buy.", bullishCondition: "Below 0.001 (green zone). HODLers are confident despite low prices.", bearishCondition: "Above 0.02 (red zone). Risk/reward unfavorable.", whyItMatters: "Captures when 'weights hands' are accumulating while price is depressed. Historically excellent at identifying asymmetric risk/reward setups.", source: "LookIntoBitcoin, Glassnode" },
      { id: "puellMultiple", name: "Puell Multiple", weight: 2, icon: Zap, description: "Compares miner revenue today vs the 365-day average. Shows when miners are under stress (capitulating) or thriving.", bullishCondition: "Below 0.5 (green zone). Miners struggling — historically marks bottoms.", bearishCondition: "Above 4 (red zone). Miners highly profitable — often near tops.", whyItMatters: "Miner economics drive significant sell pressure. When the Puell Multiple is low, the worst of miner selling is typically over.", source: "LookIntoBitcoin, Glassnode" },
      { id: "ahr999", name: "Ahr999 Index", weight: 1, icon: BarChart3, description: "Combines short-term cost basis with a geometric growth model to identify accumulation vs profit-taking zones.", bullishCondition: "Below 0.45 (dollar-cost-average zone). Below 1.2 is accumulation territory.", bearishCondition: "Above 1.2 (take profit zone).", whyItMatters: "Designed specifically to help long-term investors identify when to accumulate vs when to take profits based on valuation.", source: "LookIntoBitcoin" }
    ]
  },
  phase3: {
    title: "Phase 3: Capitulation Exhaustion",
    subtitle: "Are sellers exhausted? (Primary entry trigger zone)",
    indicators: [
      { id: "hashRibbons", name: "Hash Ribbons", weight: 3, icon: Activity, description: "Tracks when miners capitulate (30d MA crosses below 60d MA) and when they recover. 'Buy' signal fires when 30d crosses back above 60d.", bullishCondition: "Buy signal active — 30d MA crossed back above 60d MA after capitulation.", bearishCondition: "Deep capitulation ongoing — 30d MA falling further below 60d MA.", whyItMatters: "\"When miners give up, it's possibly the most powerful Bitcoin buy signal ever.\" Has caught every major cycle bottom. Your PRIMARY entry trigger.", source: "LookIntoBitcoin, Glassnode, Capriole" },
      { id: "sopr", name: "SOPR (7d MA)", weight: 2, icon: TrendingUp, description: "Spent Output Profit Ratio — measures whether coins moving on-chain are being sold at a profit (>1) or loss (<1).", bullishCondition: "Recovering above 1 after spending time below. Holders no longer selling at a loss.", bearishCondition: "Below 1 and falling. Capitulation ongoing.", whyItMatters: "When SOPR recovers above 1 after a bear market, it signals the worst of the selling is over. Confirms the turn that Hash Ribbons suggests.", source: "Glassnode, CryptoQuant" },
      { id: "lthSupply", name: "LTH Supply Trend", weight: 2, icon: Layers, description: "Tracks coins held by Long-Term Holders (155+ days). Accumulation = LTH supply increasing. Distribution = decreasing.", bullishCondition: "Rate of change turning negative (distribution starting) — signals new capital absorbing LTH selling.", bearishCondition: "Aggressive accumulation while price falling (early bear) OR aggressive distribution at highs (late bull).", whyItMatters: "LTH distribution after accumulation signals fresh capital entering. This is healthy bull market behavior.", source: "Glassnode" },
      { id: "realizedCapRoC", name: "Realized Cap Rate of Change", weight: 1, icon: TrendingUp, description: "Measures if new capital is entering (realized cap rising) or leaving (falling). Realized cap = aggregate cost basis of all BTC.", bullishCondition: "30-day rate of change turning positive. New capital entering at higher prices.", bearishCondition: "Realized cap falling. Capital leaving the network.", whyItMatters: "A rising realized cap means people are buying and holding at current prices — bullish conviction signal that upgrades your Realized Price indicator.", source: "Glassnode" }
    ]
  },
  phase4: {
    title: "Phase 4: Confirmation",
    subtitle: "Is price structure confirming the turn?",
    indicators: [
      { id: "weeklyHigherLow", name: "Weekly Higher Low", weight: 1, icon: TrendingUp, description: "Basic price structure — are weekly candles making higher lows? This confirms the trend has actually changed.", bullishCondition: "3+ consecutive weekly higher lows established.", bearishCondition: "Still making lower lows. No trend reversal confirmed.", whyItMatters: "On-chain data can be early. This confirms the market is actually ACTING like a new bull regime before you add more size.", source: "Any charting platform (TradingView)" },
      { id: "stablecoinSupply", name: "Stablecoin Supply 90d Δ", weight: 1, icon: DollarSign, description: "Tracks 90-day change in total stablecoin supply (USDT, USDC, etc). Represents 'dry powder' on the sidelines.", bullishCondition: "Supply expanding after contraction. New capital entering crypto ecosystem.", bearishCondition: "Supply contracting. Capital leaving the ecosystem.", whyItMatters: "Stablecoins are the ammunition. When supply expands, there's fresh capital ready to deploy into BTC.", source: "DefiLlama (free API)" },
      { id: "halvingCycle", name: "Halving Cycle Position", weight: 2, icon: Calendar, description: "Where are we relative to the ~4-year halving cycle? Historically, best returns come 12-18 months post-halving.", bullishCondition: "Within 6-18 months post-halving. Supply shock taking effect.", bearishCondition: "Late cycle (24+ months post-halving) or pre-halving bear.", whyItMatters: "Every halving cuts new BTC supply in half. The 12-18 month window after halving has historically produced the strongest returns.", source: "Calculate from block height (April 2024 was last halving)" }
    ]
  }
};

type Status = 'bullish' | 'neutral' | 'bearish';

const STATUS_CONFIG: Record<Status, { color: string; textColor: string; label: string; value: number }> = {
  bullish: { color: 'bg-emerald-500', textColor: 'text-emerald-400', label: 'Bullish', value: 1 },
  neutral: { color: 'bg-amber-500', textColor: 'text-amber-400', label: 'Neutral', value: 0 },
  bearish: { color: 'bg-red-500', textColor: 'text-red-400', label: 'Bearish', value: -1 }
};

const getRegimeSignal = (score: number, maxScore: number) => {
  const percentage = (score / maxScore) * 100;
  if (percentage >= 65) return { label: 'HIGH CONVICTION LONG', color: 'from-emerald-600 to-emerald-400', bgGlow: 'shadow-emerald-500/30', description: 'Multiple indicators aligned. Strong risk/reward for deployment.' };
  if (percentage >= 40) return { label: 'ACCUMULATION ZONE', color: 'from-emerald-600 to-amber-500', bgGlow: 'shadow-emerald-500/20', description: 'Early signals present. Consider scaling into position.' };
  if (percentage >= 10) return { label: 'NEUTRAL / WAIT', color: 'from-amber-600 to-amber-400', bgGlow: 'shadow-amber-500/20', description: 'Mixed signals. Wait for more confirmation.' };
  if (percentage >= -20) return { label: 'CAUTION', color: 'from-amber-600 to-red-500', bgGlow: 'shadow-amber-500/20', description: 'Bearish signals emerging. Reduce risk or stay sidelined.' };
  return { label: 'RISK OFF', color: 'from-red-600 to-red-400', bgGlow: 'shadow-red-500/30', description: 'Bear market conditions. Preserve capital.' };
};

const IndicatorCard = ({ indicator, status, onStatusChange, expanded, onToggle }: {
  indicator: Indicator;
  status: Status;
  onStatusChange: (status: Status) => void;
  expanded: boolean;
  onToggle: () => void;
}) => {
  const Icon = indicator.icon;
  const statusConfig = STATUS_CONFIG[status];

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden mb-3">
      <button onClick={onToggle} className="w-full p-4 flex items-center justify-between text-left">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className={`w-10 h-10 rounded-lg ${statusConfig.color} bg-opacity-20 flex items-center justify-center flex-shrink-0`}>
            <Icon className={`w-5 h-5 ${statusConfig.textColor}`} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-100 text-sm truncate">{indicator.name}</span>
              <span className="text-xs text-slate-500 flex-shrink-0">×{indicator.weight}</span>
            </div>
            <span className={`text-xs ${statusConfig.textColor}`}>{statusConfig.label}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${statusConfig.color}`} />
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-700/50">
          <div className="pt-4 space-y-4">
            <div className="flex gap-2">
              {(Object.entries(STATUS_CONFIG) as [Status, typeof STATUS_CONFIG[Status]][]).map(([key, config]) => (
                <button
                  key={key}
                  onClick={() => onStatusChange(key)}
                  className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-all ${
                    status === key
                      ? `${config.color} text-white`
                      : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  {config.label}
                </button>
              ))}
            </div>

            <p className="text-sm text-slate-400 leading-relaxed">{indicator.description}</p>

            <div className="space-y-2">
              <div className="flex items-start gap-2 p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <CheckCircle className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-xs font-medium text-emerald-400">Bullish when:</span>
                  <p className="text-xs text-slate-300 mt-0.5">{indicator.bullishCondition}</p>
                </div>
              </div>
              <div className="flex items-start gap-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-xs font-medium text-red-400">Bearish when:</span>
                  <p className="text-xs text-slate-300 mt-0.5">{indicator.bearishCondition}</p>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-700/30 border border-slate-600/30">
              <div className="flex items-center gap-2 mb-1">
                <Info className="w-4 h-4 text-blue-400" />
                <span className="text-xs font-semibold text-blue-400">Why This Matters</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">{indicator.whyItMatters}</p>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span>📊</span>
              <span>Source: {indicator.source}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const PhaseSection = ({ phase, phaseKey, indicators, expanded, onToggle, onIndicatorStatusChange, expandedIndicator, onIndicatorToggle }: {
  phase: Phase;
  phaseKey: string;
  indicators: Record<string, Status>;
  expanded: boolean;
  onToggle: () => void;
  onIndicatorStatusChange: (id: string, status: Status) => void;
  expandedIndicator: string | null;
  onIndicatorToggle: (id: string) => void;
}) => {
  const phaseIndicators = INDICATORS[phaseKey].indicators;
  const phaseScore = phaseIndicators.reduce((acc, ind) => {
    const status = indicators[ind.id] || 'neutral';
    return acc + (STATUS_CONFIG[status].value * ind.weight);
  }, 0);
  const maxPhaseScore = phaseIndicators.reduce((acc, ind) => acc + ind.weight, 0);

  const getPhaseStatus = () => {
    if (phaseScore > maxPhaseScore * 0.3) return { icon: CheckCircle, color: 'text-emerald-400' };
    if (phaseScore < -maxPhaseScore * 0.3) return { icon: AlertCircle, color: 'text-red-400' };
    return { icon: Clock, color: 'text-amber-400' };
  };

  const phaseStatus = getPhaseStatus();
  const PhaseIcon = phaseStatus.icon;

  return (
    <div className="mb-4">
      <button
        onClick={onToggle}
        className="w-full p-4 bg-slate-800/80 rounded-xl border border-slate-700/50 flex items-center justify-between mb-2"
      >
        <div className="flex items-center gap-3">
          <PhaseIcon className={`w-5 h-5 ${phaseStatus.color}`} />
          <div className="text-left">
            <h3 className="font-bold text-slate-100 text-sm">{phase.title}</h3>
            <p className="text-xs text-slate-500">{phase.subtitle}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-mono font-bold ${phaseStatus.color}`}>
            {phaseScore > 0 ? '+' : ''}{phaseScore}/{maxPhaseScore}
          </span>
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="pl-2">
          {phaseIndicators.map(indicator => (
            <IndicatorCard
              key={indicator.id}
              indicator={indicator}
              status={(indicators[indicator.id] as Status) || 'neutral'}
              onStatusChange={(status) => onIndicatorStatusChange(indicator.id, status)}
              expanded={expandedIndicator === indicator.id}
              onToggle={() => onIndicatorToggle(indicator.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default function BTCRegimeTracker() {
  const [indicators, setIndicators] = useState<Record<string, Status>>({});
  const [expandedPhase, setExpandedPhase] = useState<string | null>(null);
  const [expandedIndicator, setExpandedIndicator] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = window.localStorage?.getItem('btc-regime-indicators');
      if (saved) {
        const parsed = JSON.parse(saved);
        setIndicators(parsed.indicators || {});
        setLastUpdated(parsed.lastUpdated || null);
      }
    } catch (e) {
      console.log('LocalStorage not available');
    }
  }, []);

  useEffect(() => {
    if (Object.keys(indicators).length > 0) {
      try {
        const now = new Date().toISOString();
        window.localStorage?.setItem('btc-regime-indicators', JSON.stringify({ indicators, lastUpdated: now }));
        setLastUpdated(now);
      } catch (e) {
        console.log('LocalStorage not available');
      }
    }
  }, [indicators]);

  const handleIndicatorStatusChange = (id: string, status: Status) => {
    setIndicators(prev => ({ ...prev, [id]: status }));
  };

  const allIndicators = Object.values(INDICATORS).flatMap(phase => phase.indicators);
  const totalScore = allIndicators.reduce((acc, ind) => {
    const status = indicators[ind.id] || 'neutral';
    return acc + (STATUS_CONFIG[status].value * ind.weight);
  }, 0);
  const maxScore = allIndicators.reduce((acc, ind) => acc + ind.weight, 0);
  const minScore = -maxScore;
  const regime = getRegimeSignal(totalScore, maxScore);

  const resetAll = () => {
    setIndicators({});
    try { window.localStorage?.removeItem('btc-regime-indicators'); } catch (e) {}
    setLastUpdated(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-slate-950/90 backdrop-blur-lg border-b border-slate-800/50">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold text-slate-100 tracking-tight">BTC Regime Tracker</h1>
              <p className="text-xs text-slate-500">15-Indicator Framework</p>
            </div>
            <button
              onClick={resetAll}
              className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-400 transition-colors"
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* Main Signal */}
      <div className="p-4">
        <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${regime.color} p-6 shadow-2xl ${regime.bgGlow}`}>
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />
          <div className="relative text-center">
            <div className="text-5xl font-black mb-1 tracking-tighter">
              {totalScore > 0 ? '+' : ''}{totalScore}
            </div>
            <div className="text-xs text-white/70 mb-3 font-mono">
              of {maxScore} possible ({minScore} to +{maxScore})
            </div>
            <div className="inline-block px-4 py-1.5 bg-black/30 rounded-full">
              <span className="text-sm font-bold tracking-wide">{regime.label}</span>
            </div>
            <p className="text-xs text-white/80 mt-3 max-w-xs mx-auto">{regime.description}</p>
          </div>
        </div>

        {lastUpdated && (
          <div className="text-center mt-3">
            <span className="text-xs text-slate-500">
              Last updated: {new Date(lastUpdated).toLocaleDateString('en-US', {
                weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
              })}
            </span>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="px-4 mb-4">
        <div className="flex items-center justify-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span className="text-slate-400">Bullish</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className="text-slate-400">Neutral</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span className="text-slate-400">Bearish</span>
          </div>
        </div>
      </div>

      {/* Phase Sections */}
      <div className="px-4 pb-24">
        {Object.entries(INDICATORS).map(([phaseKey, phase]) => (
          <PhaseSection
            key={phaseKey}
            phase={phase}
            phaseKey={phaseKey}
            indicators={indicators}
            expanded={expandedPhase === phaseKey}
            onToggle={() => setExpandedPhase(expandedPhase === phaseKey ? null : phaseKey)}
            onIndicatorStatusChange={handleIndicatorStatusChange}
            expandedIndicator={expandedIndicator}
            onIndicatorToggle={(id) => setExpandedIndicator(expandedIndicator === id ? null : id)}
          />
        ))}

        {/* Guide */}
        <div className="mt-6 p-4 bg-slate-800/30 rounded-xl border border-slate-700/30">
          <h4 className="font-semibold text-slate-200 text-sm mb-2 flex items-center gap-2">
            <Info className="w-4 h-4 text-blue-400" />
            How to Use This
          </h4>
          <ol className="text-xs text-slate-400 space-y-2 list-decimal list-inside">
            <li><span className="text-slate-300">Every Monday:</span> Check each indicator source and update status</li>
            <li><span className="text-slate-300">Phase 1 (Macro):</span> Must be neutral/bullish — this is "permission to play"</li>
            <li><span className="text-slate-300">Phase 2 (Value):</span> Tells you if BTC is cheap, but NOT when to buy</li>
            <li><span className="text-slate-300">Phase 3 (Exhaustion):</span> Your PRIMARY entry trigger — especially Hash Ribbons</li>
            <li><span className="text-slate-300">Phase 4 (Confirm):</span> Price structure confirms the turn — add remaining size</li>
          </ol>
          <div className="mt-3 p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
            <p className="text-xs text-emerald-300">
              <strong>High conviction entry:</strong> Phase 1 supportive + Phase 2 in value zone + Hash Ribbons buy signal + SOPR recovering above 1
            </p>
          </div>
        </div>

        {/* Weight Explanation */}
        <div className="mt-4 p-4 bg-slate-800/30 rounded-xl border border-slate-700/30">
          <h4 className="font-semibold text-slate-200 text-sm mb-2">Weight System (×1, ×2, ×3)</h4>
          <div className="text-xs text-slate-400 space-y-1">
            <p><span className="text-slate-300">×3 (High conviction):</span> MVRV Z-Score, Hash Ribbons, 200-Week MA, Realized Price — near-perfect track record</p>
            <p><span className="text-slate-300">×2 (Strong signal):</span> Puell, Reserve Risk, LTH Supply, SOPR, Halving — excellent but occasionally early</p>
            <p><span className="text-slate-300">×1 (Confirming):</span> Macro indicators, stablecoins, price structure — useful confirmation but less definitive</p>
          </div>
        </div>
      </div>
    </div>
  );
}
