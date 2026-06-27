import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { num, shortDate } from "./format";
import { ETFOptionsPayload } from "./types";
import ChartShell, { ChartEmptyState } from "./ChartShell";

export default function BacktestEquity({ backtest, optionsWeeks }: { backtest: ETFOptionsPayload["backtest"]; optionsWeeks: number }) {
  const emptyMessage = `Needs more weeks of options history — currently ${optionsWeeks}`;
  const hasEnoughEquity = backtest.equity.length >= 8;

  return (
    <ChartShell title="Signal Equity vs HODL" footer="Indicative, not conclusive — limited history.">
      {optionsWeeks < 2 || !hasEnoughEquity ? (
        <ChartEmptyState message={emptyMessage} />
      ) : (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={backtest.equity} margin={{ top: 10, right: 6, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
          <XAxis dataKey="week_end" tickFormatter={shortDate} stroke="#94a3b8" fontSize={12} minTickGap={24} />
          <YAxis stroke="#94a3b8" fontSize={12} tickFormatter={(v) => `${num(Number(v), 2)}x`} width={54} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, color: "#e2e8f0" }}
            labelFormatter={(label) => shortDate(String(label))}
            formatter={(value, name) => [`${num(Number(value), 3)}x`, name === "strategy" ? "Signal" : "HODL"]}
          />
          <Line type="monotone" dataKey="strategy" dot={false} stroke="#22c55e" strokeWidth={2} />
          <Line type="monotone" dataKey="hodl" dot={false} stroke="#60a5fa" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
      )}
    </ChartShell>
  );
}
