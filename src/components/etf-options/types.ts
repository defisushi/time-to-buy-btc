export interface WeeklyRow {
  week_end: string;
  btc_close: number | null;
  btc_ret_1w: number | null;
  btc_vol_1w: number | null;
  btc_volume_1w: number | null;
  etf_net_1w: number | null;
  etf_cum: number | null;
  etf_mom_4w: number | null;
  etf_net_ibit: number | null;
  etf_net_fbtc: number | null;
  etf_net_arkb: number | null;
  etf_net_bitb: number | null;
  etf_net_gbtc: number | null;
  etf_net_hodl: number | null;
  etf_net_btco: number | null;
  etf_net_ezbc: number | null;
  etf_net_brrr: number | null;
  etf_net_btcw: number | null;
  etf_days_pos: number | null;
  opt_oi_total: number | null;
  opt_pcr_oi: number | null;
  opt_pcr_vol: number | null;
  opt_gex_net: number | null;
  opt_gamma_flip: number | null;
  opt_skew_25d_30d: number | null;
  opt_maxpain_front: number | null;
  opt_dvol: number | null;
  opt_term_slope: number | null;
  avail_date_etf: string | null;
  quality_flags: string | null;
}

export interface GexStrike {
  strike: number;
  gex: number;
}

export interface MaxPainExpiry {
  expiry: string;
  max_pain: number | null;
}

export interface LeadLagRow {
  metric: string;
  lag: number;
  corr: number | null;
  peakLag: number | null;
  interpretation: string | null;
}

export interface CorrelationRow {
  metric: string;
  shift: number;
  pearson: number | null;
  spearman: number | null;
  pval: number | null;
  fdr_pass: boolean;
}

export interface RegimeRow {
  week_end: string;
  label: string;
}

export interface SignalHistoryRow {
  week_end: string;
  conviction: number | null;
  flow_confirmation: boolean;
  bearish_divergence: boolean;
  capitulation_contrarian: boolean;
  gamma_regime: string;
}

export interface BacktestPoint {
  week_end: string;
  strategy: number;
  hodl: number;
}

export interface ETFOptionsPayload {
  lastUpdated: string;
  weekly: WeeklyRow[];
  latestSnapshot: {
    spot: number | null;
    gamma_flip: number | null;
    gexByStrike: GexStrike[];
    maxPainByExpiry: MaxPainExpiry[];
  };
  leadLag: LeadLagRow[];
  correlations: CorrelationRow[];
  regimes: RegimeRow[];
  signals: {
    conviction: number | null;
    flags: {
      flow_confirmation: boolean;
      bearish_divergence: boolean;
      capitulation_contrarian: boolean;
      gamma_regime: string;
    };
    history: SignalHistoryRow[];
  };
  backtest: {
    sharpe: number | null;
    max_dd: number | null;
    hit_rate: number | null;
    turnover: number | null;
    vs_hodl: number | null;
    equity: BacktestPoint[];
    error?: string;
  };
}
