import type {
  LiveCaptureDiagnostic,
  LiveHeroCalculation,
  LiveObservationStatus,
  MonitorSnapshot,
  RangeMatrix,
  SessionPreview,
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

export function fetchSnapshot(): Promise<MonitorSnapshot> {
  return requestJson("/v1/monitor/snapshot");
}

export function fetchReferenceRange(
  position: string,
): Promise<RangeMatrix> {
  return requestJson(
    `/v1/ranges/reference?position=${encodeURIComponent(position)}`,
  );
}

export function previewSession(input: {
  stackInput: string;
}): Promise<SessionPreview> {
  return requestJson("/v1/session/setup/preview", {
    method: "POST",
    body: JSON.stringify({
      stack_input: input.stackInput,
    }),
  });
}

export function startReplay(intervalMs = 250): Promise<unknown> {
  return requestJson("/v1/monitor/replay/start", {
    method: "POST",
    body: JSON.stringify({ interval_ms: intervalMs }),
  });
}

export function stopReplay(): Promise<unknown> {
  return requestJson("/v1/monitor/replay/stop", { method: "POST" });
}

export function runCaptureDiagnostic(): Promise<LiveCaptureDiagnostic> {
  return requestJson("/v1/capture/diagnostic", { method: "POST" });
}

export function fetchLatestCaptureDiagnostic(): Promise<LiveCaptureDiagnostic> {
  return requestJson("/v1/capture/latest/diagnostic");
}

export function fetchLiveObservationStatus(): Promise<LiveObservationStatus> {
  return requestJson("/v1/capture/live/status");
}

export function fetchLiveHeroStatus(): Promise<LiveHeroCalculation> {
  return requestJson("/v1/hero/live");
}

export function startLiveObservation(
  intervalMs = 500,
): Promise<{ started: boolean; status: LiveObservationStatus }> {
  return requestJson("/v1/capture/live/start", {
    method: "POST",
    body: JSON.stringify({ interval_ms: intervalMs }),
  });
}

export function stopLiveObservation(): Promise<{ stopped: boolean; status: LiveObservationStatus }> {
  return requestJson("/v1/capture/live/stop", { method: "POST" });
}

export function seekReplay(index: number): Promise<unknown> {
  return requestJson("/v1/monitor/replay/seek", {
    method: "POST",
    body: JSON.stringify({ index, interval_ms: 250 }),
  });
}

export function monitorWebSocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/v1/monitor/stream`;
}
