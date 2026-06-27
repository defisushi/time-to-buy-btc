import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import BacktestEquity from "./BacktestEquity";
import FlowVsPriceChart from "./FlowVsPriceChart";
import GexByStrike from "./GexByStrike";
import LeadLagHeatmap from "./LeadLagHeatmap";
import RegimeRibbon from "./RegimeRibbon";
import SkewTimeline from "./SkewTimeline";
import WeeklyFlowBars from "./WeeklyFlowBars";
import { ETFOptionsPayload } from "./types";

const payload = JSON.parse(
  readFileSync(resolve(process.cwd(), "public/etf-options-data.json"), "utf-8"),
) as ETFOptionsPayload;

const optionsWeeks = payload.weekly.filter((row) => row.opt_gex_net !== null && row.opt_gex_net !== undefined).length;
const lowSampleMessage = `Needs more weeks of options history — currently ${optionsWeeks}`;

describe("ETF/options chart components", () => {
  it("renders FlowVsPriceChart against the real payload", () => {
    render(<FlowVsPriceChart weekly={payload.weekly} />);

    expect(screen.getByText("Cumulative ETF Flow vs BTC")).toBeInTheDocument();
  });

  it("renders WeeklyFlowBars against the real payload", () => {
    render(<WeeklyFlowBars weekly={payload.weekly} />);

    expect(screen.getByText("Weekly ETF Net Flow")).toBeInTheDocument();
  });

  it("renders GexByStrike from the current option-chain snapshot", () => {
    render(<GexByStrike snapshot={payload.latestSnapshot} optionsWeeks={optionsWeeks} />);

    expect(screen.getByText("GEX by Strike")).toBeInTheDocument();
    expect(screen.queryByText(lowSampleMessage)).not.toBeInTheDocument();
  });

  it("renders SkewTimeline with the low-sample options state", () => {
    render(<SkewTimeline weekly={payload.weekly} optionsWeeks={optionsWeeks} />);

    expect(screen.getByText("25-Delta Skew vs BTC")).toBeInTheDocument();
    expect(screen.getByText(lowSampleMessage)).toBeInTheDocument();
  });

  it("renders LeadLagHeatmap with the low-sample options state", () => {
    render(<LeadLagHeatmap rows={payload.leadLag} optionsWeeks={optionsWeeks} />);

    expect(screen.getByText("Lead/Lag Correlation")).toBeInTheDocument();
    expect(screen.getByText(lowSampleMessage)).toBeInTheDocument();
  });

  it("renders RegimeRibbon against the real payload", () => {
    render(<RegimeRibbon weekly={payload.weekly} regimes={payload.regimes} />);

    expect(screen.getByText("Rule-Based Regime Ribbon")).toBeInTheDocument();
  });

  it("renders BacktestEquity with the low-sample options state and caveat", () => {
    render(<BacktestEquity backtest={payload.backtest} optionsWeeks={optionsWeeks} />);

    expect(screen.getByText("Signal Equity vs HODL")).toBeInTheDocument();
    expect(screen.getByText(lowSampleMessage)).toBeInTheDocument();
    expect(screen.getByText("Indicative, not conclusive — limited history.")).toBeInTheDocument();
  });
});
