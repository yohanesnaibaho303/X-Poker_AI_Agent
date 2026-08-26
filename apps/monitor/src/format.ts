export function formatNativeChips(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 6 }).format(value);
}

export function formatStack(valueChips: string | number): string {
  return formatNativeChips(Number(valueChips));
}

export function formatPercent(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${(value * 100).toFixed(1)}%`
    : "—";
}
