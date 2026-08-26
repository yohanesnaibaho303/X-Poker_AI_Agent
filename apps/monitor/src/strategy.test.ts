import { describe, expect, it } from "vitest";
import { buildActionRows } from "./strategy";
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
