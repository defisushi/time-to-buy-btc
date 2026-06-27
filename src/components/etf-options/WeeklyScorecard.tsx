import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowDownRight, ArrowUpRight, Gauge, ShieldAlert } from "lucide-react";
import { compactUsd, flowUsd, num } from "./format";
import { ETFOptionsPayload, WeeklyRow } from "./types";

const scoreTone = (score: number) => {
  if (score >= 30) return { text: "text-emerald-400", bg: "from-emerald-600 to-emerald-400", label: "Supportive" };
  if (score <= -30) return { text: "text-red-400", bg: "from-red-600 to-red-400", label: "Defensive" };
  return { text: "text-amber-400", bg: "from-amber-600 to-amber-400", label: "Mixed" };
};

const Metric = ({ label, value, muted = false }: { label: string; value: string; muted?: boolean }) => (
  <Card className="border-slate-700/50 bg-slate-800/50">
    <CardContent className="p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-2 text-lg font-bold ${muted ? "text-slate-400" : "text-slate-100"}`}>{value}</div>
    </CardContent>
  </Card>
);

export default function WeeklyScorecard({ payload, latest, optionsWeeks }: { payload: ETFOptionsPayload; latest: WeeklyRow; optionsWeeks: number }) {
  const score = payload.signals.conviction ?? 0;
  const tone = scoreTone(score);
  const flags = payload.signals.flags;
  const optionsHistoryLabel = `Options history: ${optionsWeeks} week(s) — accumulating`;
  const optionValue = (value: number | null | undefined, formatter: (value?: number | null) => string) => {
    if (optionsWeeks < 2 || value === null || value === undefined) return optionsHistoryLabel;
    return formatter(value);
  };

  return (
    <div className="space-y-4">
      <div className={`relative overflow-hidden rounded-xl bg-gradient-to-br ${tone.bg} p-5 shadow-xl`}>
        <div className="absolute inset-0 bg-gradient-to-t from-black/35 to-transparent" />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-white/75">
              <Gauge className="h-4 w-4" />
              <span className="text-sm font-semibold uppercase tracking-wide">ETF + Options Conviction</span>
            </div>
            <div className="mt-2 text-5xl font-black tracking-tight">{Math.round(score)}</div>
          </div>
          <div className="rounded-full bg-black/30 px-4 py-2 text-sm font-bold text-white">{tone.label}</div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Badge className="bg-slate-700 text-slate-100 hover:bg-slate-700">
          {flags.flow_confirmation ? <ArrowUpRight className="mr-1 h-3.5 w-3.5 text-emerald-400" /> : null}
          Flow confirmation {flags.flow_confirmation ? "on" : "off"}
        </Badge>
        <Badge className="bg-slate-700 text-slate-100 hover:bg-slate-700">
          {flags.bearish_divergence ? <ArrowDownRight className="mr-1 h-3.5 w-3.5 text-red-400" /> : null}
          Bearish divergence {flags.bearish_divergence ? "on" : "off"}
        </Badge>
        <Badge className="bg-slate-700 text-slate-100 hover:bg-slate-700">
          {flags.capitulation_contrarian ? <ShieldAlert className="mr-1 h-3.5 w-3.5 text-amber-400" /> : null}
          Capitulation {flags.capitulation_contrarian ? "on" : "off"}
        </Badge>
        <Badge className="bg-slate-700 text-slate-100 hover:bg-slate-700">Gamma {flags.gamma_regime}</Badge>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Metric label="Latest weekly flow" value={flowUsd(latest.etf_net_1w)} />
        <Metric label="Cumulative ETF flow" value={flowUsd(latest.etf_cum)} />
        <Metric label="Net GEX" value={optionValue(latest.opt_gex_net, compactUsd)} muted={optionsWeeks < 2 || latest.opt_gex_net == null} />
        <Metric label="25d skew" value={optionValue(latest.opt_skew_25d_30d, (value) => num(value, 2))} muted={optionsWeeks < 2 || latest.opt_skew_25d_30d == null} />
        <Metric label="DVOL" value={optionValue(latest.opt_dvol, (value) => num(value, 1))} muted={optionsWeeks < 2 || latest.opt_dvol == null} />
        <Metric label="Front max pain" value={optionValue(latest.opt_maxpain_front, compactUsd)} muted={optionsWeeks < 2 || latest.opt_maxpain_front == null} />
      </div>
    </div>
  );
}
