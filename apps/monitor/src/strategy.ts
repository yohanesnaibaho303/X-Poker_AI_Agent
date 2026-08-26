import type { MonitorSnapshot, RangeCell } from "./types";

export interface ActionRow {
  action: string;
  frequency: number;
  evChips: number | null;
}

export function buildActionRows(cell: RangeCell | null): ActionRow[] {
  if (!cell) return [];
  return Object.entries(cell.action_mix)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([action, frequency]) => ({
      action,
      frequency,
      evChips: cell.ev_chips[action] ?? null,
    }));
}

export interface StrategyComparisonRow {
  action: string;
  baseline: number | null;
  exploit: number | null;
  evChips: number | null;
  evLossChips: number | null;
}

export function buildStrategyComparisonRows(
  strategy: MonitorSnapshot["strategy"] | null,
  exploit: MonitorSnapshot["exploit"] | null,
): StrategyComparisonRow[] {
  if (!strategy || strategy.role !== "gto_solution" || strategy.status === "unavailable") return [];
  const actions = new Set([
    ...strategy.action_frequencies.map((item) => item.action),
    ...Object.keys(exploit?.adjusted_actions ?? {}),
  ]);
  return [...actions].sort().map((action) => {
    const baseline = strategy.action_frequencies.find((item) => item.action === action);
    return {
      action,
      baseline: baseline?.frequency ?? null,
      exploit: exploit?.status === "available" ? exploit.adjusted_actions[action] ?? null : null,
      evChips: baseline?.ev_chips ?? null,
      evLossChips: baseline?.ev_loss_chips ?? null,
    };
  });
}
