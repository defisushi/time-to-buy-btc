import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { flowUsd, shortDate } from "./format";
import { WeeklyRow } from "./types";
import ChartShell from "./ChartShell";

export default function WeeklyFlowBars({ weekly }: { weekly: WeeklyRow[] }) {
  const data = weekly.map((row) => ({
    week: row.week_end,
    flow: row.etf_net_1w ?? 0,
    momentum: row.etf_mom_4w ?? null,
  }));

  return (
    <ChartShell title="Weekly ETF Net Flow">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 6, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
          <XAxis dataKey="week" tickFormatter={shortDate} stroke="#94a3b8" fontSize={12} minTickGap={24} />
          <YAxis stroke="#94a3b8" fontSize={12} tickFormatter={flowUsd} width={62} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, color: "#e2e8f0" }}
            labelFormatter={(label) => shortDate(String(label))}
            formatter={(value, name) => [flowUsd(Number(value)), name === "momentum" ? "4w momentum" : "Net flow"]}
          />
          <Bar dataKey="flow" radius={[3, 3, 0, 0]}>
            {data.map((row) => (
              <Cell key={row.week} fill={row.flow >= 0 ? "#22c55e" : "#ef4444"} />
            ))}
          </Bar>
          <Line type="monotone" dataKey="momentum" dot={false} stroke="#f59e0b" strokeWidth={2} />
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

