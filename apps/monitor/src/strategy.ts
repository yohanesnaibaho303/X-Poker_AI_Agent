import type { RangeCell } from "./types";

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
