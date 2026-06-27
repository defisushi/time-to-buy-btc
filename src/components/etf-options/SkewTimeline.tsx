import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { compactUsd, num, shortDate } from "./format";
import { WeeklyRow } from "./types";
import ChartShell, { ChartEmptyState } from "./ChartShell";

export default function SkewTimeline({ weekly, optionsWeeks }: { weekly: WeeklyRow[]; optionsWeeks: number }) {
  const data = weekly.map((row) => ({
    week: row.week_end,
    skew: row.opt_skew_25d_30d ?? null,
    price: row.btc_close ?? null,
  }));
  const emptyMessage = `Needs more weeks of options history — currently ${optionsWeeks}`;

  return (
    <ChartShell title="25-Delta Skew vs BTC">
      {optionsWeeks < 2 ? (
        <ChartEmptyState message={emptyMessage} />
      ) : (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 4, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
          <XAxis dataKey="week" tickFormatter={shortDate} stroke="#94a3b8" fontSize={12} minTickGap={24} />
          <YAxis yAxisId="skew" stroke="#f59e0b" fontSize={12} tickFormatter={(v) => num(Number(v), 1)} width={52} />
          <YAxis yAxisId="price" orientation="right" stroke="#60a5fa" fontSize={12} tickFormatter={compactUsd} width={62} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, color: "#e2e8f0" }}
            labelFormatter={(label) => shortDate(String(label))}
            formatter={(value, name) => [name === "skew" ? num(Number(value), 2) : compactUsd(Number(value)), name === "skew" ? "25d RR" : "BTC"]}
          />
          <Line yAxisId="skew" type="monotone" dataKey="skew" dot={false} stroke="#f59e0b" strokeWidth={2} />
          <Line yAxisId="price" type="monotone" dataKey="price" dot={false} stroke="#60a5fa" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
      )}
    </ChartShell>
  );
}
