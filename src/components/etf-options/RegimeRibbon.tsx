import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { compactUsd, shortDate } from "./format";
import { RegimeRow, WeeklyRow } from "./types";
import ChartShell from "./ChartShell";

const regimeFill = (label: string) => {
  if (label.includes("Bull") && label.includes("Calm")) return "#22c55e";
  if (label.includes("Bull")) return "#84cc16";
  if (label.includes("Calm")) return "#38bdf8";
  if (label.includes("Bear")) return "#ef4444";
  return "#64748b";
};

export default function RegimeRibbon({ weekly, regimes }: { weekly: WeeklyRow[]; regimes: RegimeRow[] }) {
  const regimeByWeek = new Map(regimes.map((row) => [row.week_end, row.label]));
  const data = weekly.map((row) => ({
    week: row.week_end,
    price: row.btc_close ?? null,
    label: regimeByWeek.get(row.week_end) ?? "Unknown",
  }));
  const spans = data.reduce<Array<{ start: string; end: string; label: string }>>((acc, row) => {
    const last = acc[acc.length - 1];
    if (!last || last.label !== row.label) {
      acc.push({ start: row.week, end: row.week, label: row.label });
    } else {
      last.end = row.week;
    }
    return acc;
  }, []);

  return (
    <ChartShell title="Rule-Based Regime Ribbon">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 6, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
          <XAxis dataKey="week" tickFormatter={shortDate} stroke="#94a3b8" fontSize={12} minTickGap={24} />
          <YAxis yAxisId="price" stroke="#60a5fa" fontSize={12} tickFormatter={compactUsd} width={62} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, color: "#e2e8f0" }}
            labelFormatter={(label) => shortDate(String(label))}
            formatter={(value, name, item) => {
              return [`${compactUsd(Number(value))} · ${item.payload.label}`, name === "price" ? "BTC" : "Regime"];
            }}
          />
          {spans.map((span) => (
            <ReferenceArea
              key={`${span.start}-${span.label}`}
              yAxisId="price"
              x1={span.start}
              x2={span.end}
              fill={regimeFill(span.label)}
              fillOpacity={0.14}
              strokeOpacity={0}
            />
          ))}
          <Line yAxisId="price" type="monotone" dataKey="price" dot={false} stroke="#60a5fa" strokeWidth={2} />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
