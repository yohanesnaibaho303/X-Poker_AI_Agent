import type {
  ChipMode,
  MonitorSnapshot,
  RangeMatrix,
  SessionPreview,
  TableSize,
} from "./types";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  return (await response.json()) as T;
}

export function fetchSnapshot(tableSize: TableSize): Promise<MonitorSnapshot> {
  return requestJson(`/v1/monitor/snapshot?table_size=${tableSize}`);
}

export function fetchReferenceRange(
  tableSize: TableSize,
  position: string,
): Promise<RangeMatrix> {
  return requestJson(
    `/v1/ranges/reference?table_size=${tableSize}&position=${encodeURIComponent(position)}`,
  );
}

export function previewSession(input: {
  tableSize: TableSize;
  chipMode: ChipMode;
  stackInput: string;
  bigBlindNative: number | null;
}): Promise<SessionPreview> {
  return requestJson("/v1/session/setup/preview", {
    method: "POST",
    body: JSON.stringify({
      table_size: input.tableSize,
      chip_display_mode: input.chipMode,
      stack_input: input.stackInput,
      big_blind_native_chips: input.bigBlindNative,
    }),
  });
}

export function startReplay(tableSize: TableSize, intervalMs = 250): Promise<unknown> {
  return requestJson("/v1/monitor/replay/start", {
    method: "POST",
    body: JSON.stringify({ table_size: tableSize, interval_ms: intervalMs }),
  });
}

export function stopReplay(): Promise<unknown> {
  return requestJson("/v1/monitor/replay/stop", { method: "POST" });
}

export function monitorWebSocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/v1/monitor/stream`;
}
