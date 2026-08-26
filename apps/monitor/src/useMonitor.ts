import { useCallback, useEffect, useRef, useState } from "react";
import { fetchSnapshot, monitorWebSocketUrl } from "./api";
import { applyEnvelope, initialStreamState, type StreamState } from "./stream";
import type { MonitorEnvelope } from "./types";

export type ConnectionStatus = "connecting" | "live" | "recovering" | "offline";

export function useMonitor() {
  const [stream, setStream] = useState<StreamState>(initialStreamState);
  const [connection, setConnection] = useState<ConnectionStatus>("connecting");
  const [error, setError] = useState<string | null>(null);
  const streamRef = useRef(stream);

  useEffect(() => {
    streamRef.current = stream;
  }, [stream]);

  const refresh = useCallback(async () => {
    setConnection("recovering");
    try {
      const snapshot = await fetchSnapshot();
      const next = {
        snapshot,
        lastSequence: snapshot.sequence,
        gapDetected: false,
      };
      streamRef.current = next;
      setStream(next);
      setError(null);
      setConnection("live");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Snapshot request failed");
      setConnection("offline");
    }
  }, []);

  useEffect(() => {
    let disposed = false;
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let attempts = 0;

    void refresh();

    const connect = () => {
      if (disposed) return;
      setConnection("connecting");
      socket = new WebSocket(monitorWebSocketUrl());
      socket.onopen = () => {
        attempts = 0;
        setConnection("live");
      };
      socket.onmessage = (message) => {
        const envelope = JSON.parse(String(message.data)) as MonitorEnvelope;
        const next = applyEnvelope(streamRef.current, envelope);
        streamRef.current = next;
        setStream(next);
        if (next.gapDetected) void refresh();
      };
      socket.onerror = () => setError("Monitor stream connection failed");
      socket.onclose = () => {
        if (disposed) return;
        setConnection("offline");
        const delay = Math.min(5_000, 500 * 2 ** attempts++);
        retry = setTimeout(connect, delay);
      };
    };
    connect();
    return () => {
      disposed = true;
      if (retry) clearTimeout(retry);
      socket?.close();
    };
  }, [refresh]);

  return { ...stream, connection, error, refresh };
}
