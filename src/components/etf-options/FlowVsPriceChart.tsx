import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { compactUsd, flowUsd, shortDate } from "./format";
import { WeeklyRow } from "./types";
import ChartShell from "./ChartShell";

export default function FlowVsPriceChart({ weekly }: { weekly: WeeklyRow[] }) {
  const data = weekly.map((row) => ({
    week: row.week_end,
    flow: row.etf_cum ?? null,
    price: row.btc_close ?? null,
  }));

  return (
    <ChartShell title="Cumulative ETF Flow vs BTC">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 4, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
          <XAxis dataKey="week" tickFormatter={shortDate} stroke="#94a3b8" fontSize={12} minTickGap={24} />
          <YAxis yAxisId="flow" stroke="#22c55e" fontSize={12} tickFormatter={flowUsd} width={62} />
          <YAxis yAxisId="price" orientation="right" stroke="#60a5fa" fontSize={12} tickFormatter={compactUsd} width={62} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, color: "#e2e8f0" }}
            labelFormatter={(label) => shortDate(String(label))}
            formatter={(value, name) => [name === "flow" ? flowUsd(Number(value)) : compactUsd(Number(value)), name === "flow" ? "ETF flow" : "BTC"]}
          />
          <Area yAxisId="flow" type="monotone" dataKey="flow" fill="#22c55e33" stroke="#22c55e" strokeWidth={2} />
          <Line yAxisId="price" type="monotone" dataKey="price" dot={false} stroke="#60a5fa" strokeWidth={2} />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

