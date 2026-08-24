import type { MonitorEnvelope, MonitorSnapshot } from "./types";

export interface StreamState {
  snapshot: MonitorSnapshot | null;
  lastSequence: number;
  gapDetected: boolean;
}

export const initialStreamState: StreamState = {
  snapshot: null,
  lastSequence: 0,
  gapDetected: false,
};

export function applyEnvelope(state: StreamState, envelope: MonitorEnvelope): StreamState {
  if (envelope.kind === "heartbeat" || envelope.sequence <= state.lastSequence) return state;
  const gapDetected = state.lastSequence > 0 && envelope.sequence > state.lastSequence + 1;
  const rawSnapshot =
    envelope.kind === "snapshot" ? envelope.payload : envelope.payload.snapshot;
  const snapshot = rawSnapshot
    ? ({ ...(rawSnapshot as MonitorSnapshot), sequence: envelope.sequence } as MonitorSnapshot)
    : state.snapshot;
  return {
    snapshot,
    lastSequence: envelope.sequence,
    gapDetected,
  };
}
