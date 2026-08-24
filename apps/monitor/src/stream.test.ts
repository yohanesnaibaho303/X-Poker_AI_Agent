import { describe, expect, it } from "vitest";
import { applyEnvelope, type StreamState } from "./stream";
import type { MonitorEnvelope, MonitorSnapshot } from "./types";

const snapshot = { sequence: 0, table_size: 6 } as MonitorSnapshot;

function envelope(sequence: number): MonitorEnvelope {
  return {
    schema_version: "1.0",
    sequence,
    kind: "event",
    payload: { snapshot },
  };
}

describe("monitor stream reducer", () => {
  it("advances ordered envelopes", () => {
    const start: StreamState = { snapshot, lastSequence: 4, gapDetected: false };
    const result = applyEnvelope(start, envelope(5));
    expect(result.lastSequence).toBe(5);
    expect(result.gapDetected).toBe(false);
    expect(result.snapshot?.sequence).toBe(5);
  });

  it("detects missing sequences for snapshot recovery", () => {
    const start: StreamState = { snapshot, lastSequence: 4, gapDetected: false };
    expect(applyEnvelope(start, envelope(7)).gapDetected).toBe(true);
  });

  it("ignores duplicate and stale envelopes", () => {
    const start: StreamState = { snapshot, lastSequence: 4, gapDetected: false };
    expect(applyEnvelope(start, envelope(4))).toBe(start);
  });
});
