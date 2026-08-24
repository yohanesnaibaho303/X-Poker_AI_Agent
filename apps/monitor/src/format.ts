import type { ChipMode } from "./types";

function compact(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(6)));
}

export function formatNativeChips(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "—";
  if (value >= 1_000_000) return `${compact(value / 1_000_000)}M`;
  if (value >= 100_000) return `${compact(value / 1_000)}K`;
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 6 }).format(value);
}

export function formatStack(
  valueBb: string | number,
  mode: ChipMode,
  bigBlindNative: number | null,
): string {
  const bb = Number(valueBb);
  if (!Number.isFinite(bb)) return "—";
  if (mode === "BB") return `${compact(bb)}BB`;
  if (bigBlindNative === null || bigBlindNative <= 0) return "blind required";
  return formatNativeChips(bb * bigBlindNative);
}

export function formatPercent(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${(value * 100).toFixed(1)}%`
    : "—";
}
