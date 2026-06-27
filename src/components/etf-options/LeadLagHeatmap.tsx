import { Fragment } from "react";
import { LeadLagRow } from "./types";
import ChartShell, { ChartEmptyState } from "./ChartShell";

const colorFor = (corr?: number | null) => {
  if (corr === null || corr === undefined || Number.isNaN(corr)) return "rgba(51,65,85,0.45)";
  const alpha = Math.min(Math.abs(corr), 1);
  return corr >= 0 ? `rgba(34,197,94,${0.15 + alpha * 0.75})` : `rgba(239,68,68,${0.15 + alpha * 0.75})`;
};

const metricLabel = (metric: string) =>
  metric
    .replace("etf_", "ETF ")
    .replace("opt_", "OPT ")
    .replaceAll("_", " ")
    .toUpperCase();

export default function LeadLagHeatmap({ rows, optionsWeeks }: { rows: LeadLagRow[]; optionsWeeks: number }) {
  const metrics = Array.from(new Set(rows.map((row) => row.metric)));
  const lags = Array.from(new Set(rows.map((row) => row.lag))).sort((a, b) => a - b);
  const lookup = new Map(rows.map((row) => [`${row.metric}:${row.lag}`, row]));
  const emptyMessage = `Needs more weeks of options history — currently ${optionsWeeks}`;

  return (
    <ChartShell title="Lead/Lag Correlation">
      {optionsWeeks < 2 || rows.every((row) => row.corr === null || row.corr === undefined) ? (
        <ChartEmptyState message={emptyMessage} />
      ) : (
      <div className="h-full overflow-x-auto">
        <div
          className="grid min-w-[660px] gap-1 text-xs"
          style={{ gridTemplateColumns: `132px repeat(${lags.length}, minmax(24px, 1fr))` }}
        >
          <div />
          {lags.map((lag) => (
            <div key={lag} className="text-center text-slate-500">
              {lag}
            </div>
          ))}
          {metrics.map((metric) => (
            <Fragment key={metric}>
              <div className="truncate pr-2 text-slate-300">
                {metricLabel(metric)}
              </div>
              {lags.map((lag) => {
                const row = lookup.get(`${metric}:${lag}`);
                return (
                  <div
                    key={`${metric}-${lag}`}
                    className="h-7 rounded border border-slate-900/50"
                    title={`${metricLabel(metric)} lag ${lag}: ${row?.corr?.toFixed(3) ?? "n/a"}`}
                    style={{ backgroundColor: colorFor(row?.corr) }}
                  />
                );
              })}
            </Fragment>
          ))}
        </div>
      </div>
      )}
    </ChartShell>
  );
}
