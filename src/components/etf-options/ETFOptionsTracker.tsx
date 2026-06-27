import SiteNav from "@/components/SiteNav";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useQuery } from "@tanstack/react-query";
import BacktestEquity from "./BacktestEquity";
import FlowVsPriceChart from "./FlowVsPriceChart";
import GexByStrike from "./GexByStrike";
import LeadLagHeatmap from "./LeadLagHeatmap";
import RegimeRibbon from "./RegimeRibbon";
import SkewTimeline from "./SkewTimeline";
import WeeklyFlowBars from "./WeeklyFlowBars";
import WeeklyScorecard from "./WeeklyScorecard";
import { ETFOptionsPayload } from "./types";

const fetchPayload = async (): Promise<ETFOptionsPayload> => {
  const response = await fetch(`${import.meta.env.BASE_URL}etf-options-data.json?t=${Date.now()}`);
  if (!response.ok) {
    throw new Error(`Failed to load ETF/options data (${response.status})`);
  }
  return response.json();
};

export default function ETFOptionsTracker() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["etf-options-data"],
    queryFn: fetchPayload,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white">
        <div className="mx-auto w-full max-w-6xl px-4 py-6">
          <div className="mb-6 max-w-md">
            <SiteNav />
          </div>
          <Skeleton className="h-44 rounded-xl bg-slate-800" />
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Skeleton className="h-80 rounded-xl bg-slate-800" />
            <Skeleton className="h-80 rounded-xl bg-slate-800" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white">
        <div className="mx-auto w-full max-w-3xl px-4 py-6">
          <SiteNav />
          <Alert className="mt-6 border-red-500/30 bg-red-950/40 text-red-100">
            <AlertDescription>{error instanceof Error ? error.message : "ETF/options data is unavailable."}</AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  const latest = data.weekly[data.weekly.length - 1];
  const sampleWeeks = data.weekly.length;
  const optionsWeeks = data.weekly.filter((row) => row.opt_gex_net !== null && row.opt_gex_net !== undefined).length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white">
      <div className="mx-auto w-full max-w-6xl px-4 py-6">
        <header className="mb-5 space-y-4">
          <div className="max-w-md">
            <SiteNav />
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">BTC ETF Flows + Options</h1>
              <p className="mt-1 text-slate-400">Weekly flow, gamma, skew, and regime monitor</p>
            </div>
            <div className="text-sm text-slate-500">
              Updated {new Date(data.lastUpdated).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-slate-500">
            <span className="rounded-md border border-slate-700/50 bg-slate-800/50 px-2 py-1">{sampleWeeks} flow/price weeks</span>
            <span className="rounded-md border border-slate-700/50 bg-slate-800/50 px-2 py-1">{optionsWeeks} options weeks</span>
          </div>
        </header>

        <main className="space-y-4">
          <WeeklyScorecard payload={data} latest={latest} optionsWeeks={optionsWeeks} />
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="lg:col-span-2">
              <FlowVsPriceChart weekly={data.weekly} />
            </div>
            <WeeklyFlowBars weekly={data.weekly} />
            <RegimeRibbon weekly={data.weekly} regimes={data.regimes} />
            <GexByStrike snapshot={data.latestSnapshot} optionsWeeks={optionsWeeks} />
            <SkewTimeline weekly={data.weekly} optionsWeeks={optionsWeeks} />
            <LeadLagHeatmap rows={data.leadLag} optionsWeeks={optionsWeeks} />
            <BacktestEquity backtest={data.backtest} optionsWeeks={optionsWeeks} />
          </div>
        </main>
      </div>
    </div>
  );
}
