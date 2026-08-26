import { describe, expect, it } from "vitest";
import { buildActionRows, buildStrategyComparisonRows } from "./strategy";
import type { RangeCell } from "./types";

const cell: RangeCell = {
  hand_class: "AA",
  row: 0,
  column: 0,
  possible_combos: 6,
  included_combos: 6,
  combo_weight: 6,
  inclusion_frequency: 1,
  action_mix: { "raise@4chips": 0.9, fold: 0.1 },
  unassigned_action_frequency: 0,
  equity: 0.82,
  ev_chips: { "raise@4chips": 3.5, fold: 0 },
};

describe("buildActionRows", () => {
  it("keeps native-chip EV aligned with deterministically sorted actions", () => {
    expect(buildActionRows(cell)).toEqual([
      { action: "fold", frequency: 0.1, evChips: 0 },
      { action: "raise@4chips", frequency: 0.9, evChips: 3.5 },
    ]);
  });

  it("returns no invented rows when strategy is unavailable", () => {
    expect(buildActionRows(null)).toEqual([]);
  });
});

describe("buildStrategyComparisonRows", () => {
  it("withholds reference priors from the GTO comparison", () => {
    expect(buildStrategyComparisonRows({ role: "reference_prior", status: "unavailable" } as never, null)).toEqual([]);
  });

  it("joins exact GTO and available exploit frequencies", () => {
    const rows = buildStrategyComparisonRows(
      {
        role: "gto_solution",
        status: "exact",
        action_frequencies: [
          { action: "fold", frequency: 0.25, ev_chips: 0, ev_loss_chips: 2 },
          { action: "raise@6chips", frequency: 0.75, ev_chips: 4, ev_loss_chips: 0 },
        ],
      } as never,
      { status: "available", adjusted_actions: { fold: 0.1, "raise@6chips": 0.9 } } as never,
    );
    expect(rows).toEqual([
      { action: "fold", baseline: 0.25, exploit: 0.1, evChips: 0, evLossChips: 2 },
      { action: "raise@6chips", baseline: 0.75, exploit: 0.9, evChips: 4, evLossChips: 0 },
    ]);
  });
});
