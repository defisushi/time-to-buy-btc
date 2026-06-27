import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { HashRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ETFOptionsTracker from "./ETFOptionsTracker";
import { ETFOptionsPayload } from "./types";

const payload = JSON.parse(
  readFileSync(resolve(process.cwd(), "public/etf-options-data.json"), "utf-8"),
) as ETFOptionsPayload;

const renderTracker = () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <HashRouter>
        <ETFOptionsTracker />
      </HashRouter>
    </QueryClientProvider>,
  );
};

describe("ETFOptionsTracker", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => payload,
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the scorecard and charts from the real payload", async () => {
    renderTracker();

    expect(await screen.findByText("BTC ETF Flows + Options")).toBeInTheDocument();
    expect(screen.getByText("ETF + Options Conviction")).toBeInTheDocument();
    expect(screen.getByText("Cumulative ETF Flow vs BTC")).toBeInTheDocument();
    expect(screen.getByText("Weekly ETF Net Flow")).toBeInTheDocument();
    expect(screen.getByText("Lead/Lag Correlation")).toBeInTheDocument();
    expect(screen.getByText("GEX by Strike")).toBeInTheDocument();
    expect(screen.getByText("Signal Equity vs HODL")).toBeInTheDocument();
    expect(screen.getAllByText(/Needs more weeks of options history — currently \d+/).length).toBeGreaterThan(0);
  });
});
