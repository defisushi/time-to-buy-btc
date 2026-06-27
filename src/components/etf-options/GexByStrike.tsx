import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { compactUsd } from "./format";
import { ETFOptionsPayload } from "./types";
import ChartShell, { ChartEmptyState } from "./ChartShell";

export default function GexByStrike({ snapshot }: { snapshot: ETFOptionsPayload["latestSnapshot"]; optionsWeeks: number }) {
  const maxAbsGex = Math.max(...snapshot.gexByStrike.map((row) => Math.abs(row.gex)), 0);
  const minVisibleGex = maxAbsGex * 0.01;
  const lowerStrike = snapshot.spot ? snapshot.spot * 0.5 : Number.NEGATIVE_INFINITY;
  const upperStrike = snapshot.spot ? snapshot.spot * 1.5 : Number.POSITIVE_INFINITY;
  const filtered = snapshot.gexByStrike.filter(
    (row) => row.strike >= lowerStrike && row.strike <= upperStrike && Math.abs(row.gex) >= minVisibleGex,
  );
  const data = filtered.length > 0 ? filtered : snapshot.gexByStrike;
  const strikeDomain = data.length > 0 ? ([data[0].strike, data[data.length - 1].strike] as [number, number]) : undefined;
  const frontMaxPain = snapshot.maxPainByExpiry[0]?.max_pain ?? null;

  return (
    <ChartShell title="GEX by Strike">
      {snapshot.gexByStrike.length === 0 ? (
        <ChartEmptyState message="No current options chain available." />
      ) : (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 8, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
          <XAxis
            dataKey="strike"
            type="number"
            domain={strikeDomain}
            stroke="#94a3b8"
            fontSize={12}
            tickFormatter={compactUsd}
            minTickGap={18}
          />
          <YAxis stroke="#94a3b8" fontSize={12} tickFormatter={(v) => compactUsd(Number(v))} width={62} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, color: "#e2e8f0" }}
            formatter={(value) => [compactUsd(Number(value)), "GEX"]}
            labelFormatter={(label) => `Strike ${compactUsd(Number(label))}`}
          />
          {snapshot.spot ? <ReferenceLine x={snapshot.spot} stroke="#60a5fa" label={{ value: "spot", fill: "#93c5fd", fontSize: 11 }} /> : null}
          {snapshot.gamma_flip ? <ReferenceLine x={snapshot.gamma_flip} stroke="#f59e0b" label={{ value: "flip", position: "insideTop", fill: "#fbbf24", fontSize: 11, dy: 14 }} /> : null}
          {frontMaxPain ? <ReferenceLine x={frontMaxPain} stroke="#c084fc" label={{ value: "max pain", position: "insideBottom", fill: "#d8b4fe", fontSize: 11, dy: -6 }} /> : null}
          <Bar dataKey="gex" radius={[3, 3, 0, 0]}>
            {data.map((row) => (
              <Cell key={row.strike} fill={row.gex >= 0 ? "#22c55e" : "#ef4444"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      )}
    </ChartShell>
  );
}
