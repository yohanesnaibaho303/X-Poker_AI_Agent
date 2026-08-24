import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import {
  fetchLatestCaptureDiagnostic,
  fetchLiveObservationStatus,
  fetchReferenceRange,
  previewSession,
  runCaptureDiagnostic,
  seekReplay,
  startReplay,
  startLiveObservation,
  stopLiveObservation,
  stopReplay,
} from "./api";
import { formatPercent, formatStack } from "./format";
import type {
  ChipMode,
  HandEvent,
  HandState,
  LiveCaptureDiagnostic,
  LiveObservationStatus,
  RangeMatrix,
  SessionPreview,
  TableSize,
} from "./types";
import { useMonitor } from "./useMonitor";

const POSITIONS: Record<TableSize, string[]> = {
  6: ["UTG", "HJ", "CO", "BTN", "SB"],
  9: ["UTG", "UTG+1", "MP", "LJ", "HJ", "CO", "BTN", "SB"],
};

function Card({ value }: { value: string }) {
  const suit = value.at(-1);
  return (
    <span className={`card suit-${suit ?? "x"}`}>
      <strong>{value.slice(0, -1)}</strong>
      <small>{{ c: "♣", d: "♦", h: "♥", s: "♠" }[suit ?? ""] ?? "?"}</small>
    </span>
  );
}

function StatusPill({ tone, children }: { tone: string; children: ReactNode }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function TableCanvas({
  state,
  chipMode,
  bigBlindNative,
}: {
  state: HandState;
  chipMode: ChipMode;
  bigBlindNative: number | null;
}) {
  return (
    <section className="table-stage panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Reconstructed table</p>
          <h2>{state.table_size}-max · {state.street}</h2>
        </div>
        <StatusPill tone={state.validation.legal ? "ok" : "danger"}>
          {state.validation.legal ? "State legal" : "State quarantined"}
        </StatusPill>
      </div>
      <div className={`poker-table seats-${state.table_size}`}>
        <div className="felt-rim" />
        <div className="board-zone">
          <span className="pot-label">Pot {formatStack(state.pot_main_bb, chipMode, bigBlindNative)}</span>
          <div className="board-cards">
            {state.board.length ? state.board.map((card) => <Card key={card} value={card} />) : <em>Board waiting</em>}
          </div>
          <span className="street-label">{state.table_status.replaceAll("_", " ")}</span>
        </div>
        {state.seats.map((seat, index) => {
          const angle = (index / state.table_size) * Math.PI * 2 + Math.PI / 2;
          const left = 50 + Math.cos(angle) * 44;
          const top = 50 + Math.sin(angle) * 43;
          const isHero = seat.seat === state.hero_seat;
          const active = seat.seat === state.next_to_act_seat;
          return (
            <div
              className={`seat ${seat.participation} ${isHero ? "hero" : ""} ${active ? "acting" : ""}`}
              key={seat.seat}
              style={{ left: `${left}%`, top: `${top}%` }}
            >
              <div className="seat-topline">
                <span>{seat.position ?? `Seat ${seat.seat + 1}`}</span>
                {state.dealer_seat === seat.seat && <b className="dealer">D</b>}
              </div>
              <strong>{isHero ? "Hero" : seat.participation.replaceAll("_", " ")}</strong>
              <small>{formatStack(seat.stack_bb, chipMode, bigBlindNative)}</small>
              {isHero && state.hero_cards.length > 0 && (
                <div className="mini-cards">{state.hero_cards.join(" ")}</div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ActionHistory({ events }: { events: HandEvent[] }) {
  return (
    <section className="panel history-panel">
      <div className="panel-heading compact">
        <div>
          <p className="eyebrow">Canonical stream</p>
          <h3>Action history</h3>
        </div>
        <span className="counter">{events.length}</span>
      </div>
      <div className="history-list">
        {events.length === 0 && <p className="empty-copy">Start the replay to inspect validated transitions.</p>}
        {[...events].reverse().map((event) => (
          <article key={event.event_id} className="history-row">
            <span className={`event-dot ${event.category}`} />
            <div>
              <strong>{event.type.replaceAll("_", " ")}</strong>
              <small>
                #{event.sequence} · {event.street}
                {event.actor_seat !== null ? ` · seat ${event.actor_seat + 1}` : ""}
              </small>
            </div>
            <span className="confidence">{formatPercent(event.confidence.score)}</span>
          </article>
        ))}
      </div>
    </section>
  );
}

function RangeGrid({ matrix, loading }: { matrix: RangeMatrix | null; loading: boolean }) {
  return (
    <section className="panel range-panel">
      <div className="panel-heading compact">
        <div>
          <p className="eyebrow">Combination strategy</p>
          <h3>Reference prior matrix</h3>
        </div>
        <StatusPill tone="warn">Not GTO</StatusPill>
      </div>
      {loading && <div className="matrix-skeleton">Loading 1,326 combinations…</div>}
      {!loading && matrix && (
        <>
          <div className="range-grid" aria-label="13 by 13 reference range matrix">
            {matrix.cells.map((cell) => {
              const raise = cell.action_mix["raise@2bb"] ?? 0;
              return (
                <div
                  className="range-cell"
                  key={cell.hand_class}
                  style={{ "--raise": raise } as CSSProperties}
                  title={`${cell.hand_class}: raise ${(raise * 100).toFixed(0)}%`}
                >
                  {cell.hand_class}
                </div>
              );
            })}
          </div>
          <div className="range-meta">
            <span>Confidence {formatPercent(matrix.confidence)}</span>
            <span>{String(matrix.source.strategy_role ?? "reference_prior")}</span>
          </div>
        </>
      )}
    </section>
  );
}

function CapturePreview({ diagnostic, nonce }: { diagnostic: LiveCaptureDiagnostic; nonce: number }) {
  const occupiedSeats = diagnostic.seat_observations.filter((seat) => seat.status === "occupied").length;
  const ambiguousSeats = diagnostic.seat_observations.filter((seat) => seat.status === "ambiguous").length;
  const stackCandidates = diagnostic.seat_panels.filter((seat) => seat.stack_native !== null).length;
  return (
    <section className="panel capture-panel">
      <div className="panel-heading compact">
        <div><p className="eyebrow">Authorized evidence</p><h3>Live X-Poker capture</h3></div>
        <StatusPill tone={diagnostic.current_hand_supported ? "ok" : "danger"}>
          {diagnostic.current_hand_supported
            ? diagnostic.current_hand_mode.replaceAll("_", " ")
            : "Quarantined"}
        </StatusPill>
      </div>
      <div className="capture-frame">
        <img src={`/v1/capture/latest.bmp?v=${nonce}`} alt="Latest authorized X-Poker table capture" />
        {Object.entries(diagnostic.regions).map(([name, [x, y, width, height]]) => (
          <span
            className={`capture-overlay region-${name}`}
            key={name}
            style={{ left: `${x * 100}%`, top: `${y * 100}%`, width: `${width * 100}%`, height: `${height * 100}%` }}
            title={name}
          />
        ))}
      </div>
      <div className="capture-facts">
        <span>Role confidence <strong>{formatPercent(diagnostic.visual_role_confidence)}</strong></span>
        <span>OCR <strong>{diagnostic.ocr_latency_ms.toFixed(1)} ms</strong></span>
      </div>
      <div className="capture-facts">
        <span>Layout <strong>{diagnostic.table_size}-max</strong></span>
        <span>Seats <strong>{occupiedSeats}/{diagnostic.table_size} occupied{ambiguousSeats ? ` · ${ambiguousSeats} ambiguous` : ""}</strong></span>
      </div>
      <div className="capture-facts">
        <span>Board <strong>{diagnostic.board_card_slots} cards · {diagnostic.board_rows} row</strong></span>
        <span>Card candidates <strong>{diagnostic.board_cards.map((card) => card.card ?? "?").join(" ") || "—"}</strong></span>
        <span>Geometry <strong>{diagnostic.board_geometry_supported ? "Supported" : "Quarantined"}</strong></span>
      </div>
      <div className="capture-facts">
        <span>Stack candidates <strong>{stackCandidates}/{occupiedSeats}</strong></span>
        <span>Acceptance <strong>Temporal gate pending</strong></span>
      </div>
      <p className={`mode-copy ${diagnostic.current_hand_supported ? "supported" : "quarantined"}`}>
        {diagnostic.mode_reason}
      </p>
      {diagnostic.bomb_pot_state === "scheduled" && diagnostic.hands_until_bomb !== null && (
        <small>Bomb Pot scheduled after {diagnostic.hands_until_bomb} hand{diagnostic.hands_until_bomb === 1 ? "" : "s"}</small>
      )}
      {diagnostic.bomb_pot_state === "scheduled" && diagnostic.bomb_pot_interval_hands !== null && (
        <small>Bomb Pot configured every {diagnostic.bomb_pot_interval_hands} hands</small>
      )}
      <small>{diagnostic.rule_text || "No rule label recognized"}</small>
    </section>
  );
}

export default function App() {
  const [tableSize, setTableSize] = useState<TableSize>(6);
  const [chipMode, setChipMode] = useState<ChipMode>("BB");
  const [stackInput, setStackInput] = useState("100");
  const [bigBlindText, setBigBlindText] = useState("2000");
  const [position, setPosition] = useState("BTN");
  const [session, setSession] = useState<SessionPreview | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [matrix, setMatrix] = useState<RangeMatrix | null>(null);
  const [matrixLoading, setMatrixLoading] = useState(false);
  const [captureDiagnostic, setCaptureDiagnostic] = useState<LiveCaptureDiagnostic | null>(null);
  const [liveObservation, setLiveObservation] = useState<LiveObservationStatus | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [captureNonce, setCaptureNonce] = useState(0);
  const { snapshot, connection, error, refresh } = useMonitor(tableSize);

  const bigBlindNative = useMemo(() => {
    const parsed = Number(bigBlindText.replaceAll(",", ""));
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }, [bigBlindText]);

  useEffect(() => {
    if (!POSITIONS[tableSize].includes(position)) setPosition("BTN");
    setMatrixLoading(true);
    fetchReferenceRange(tableSize, position)
      .then(setMatrix)
      .catch(() => setMatrix(null))
      .finally(() => setMatrixLoading(false));
  }, [position, tableSize]);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const status = await fetchLiveObservationStatus();
        if (!mounted) return;
        setLiveObservation(status);
        if (status.latest_sequence > 0) {
          const diagnostic = await fetchLatestCaptureDiagnostic();
          if (!mounted) return;
          setCaptureDiagnostic(diagnostic);
          setCaptureNonce(Date.now());
          setCaptureError(status.last_error);
        }
      } catch (reason) {
        if (mounted) {
          setCaptureError(reason instanceof Error ? reason.message : "Live observation poll failed");
        }
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 1000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const validateSession = async () => {
    try {
      const result = await previewSession({
        tableSize,
        chipMode,
        stackInput,
        bigBlindNative: chipMode === "native" ? bigBlindNative : null,
      });
      setSession(result);
      setSessionError(null);
    } catch (reason) {
      setSession(null);
      setSessionError(reason instanceof Error ? reason.message : "Session validation failed");
    }
  };

  const runReplay = async () => {
    await startReplay(tableSize, 250);
    await refresh();
  };

  const seek = async (index: number) => {
    await seekReplay(tableSize, Math.max(0, Math.min(14, index)));
  };

  const inspectCapture = async () => {
    try {
      const result = await runCaptureDiagnostic(tableSize);
      setCaptureDiagnostic(result);
      setCaptureNonce(Date.now());
      setCaptureError(null);
    } catch (reason) {
      setCaptureError(reason instanceof Error ? reason.message : "Capture diagnostic failed");
    }
  };

  const startLiveCapture = async () => {
    try {
      const result = await startLiveObservation(tableSize, 500);
      setLiveObservation(result.status);
      setCaptureError(null);
    } catch (reason) {
      setCaptureError(reason instanceof Error ? reason.message : "Live observation failed to start");
    }
  };

  const stopLiveCapture = async () => {
    const result = await stopLiveObservation();
    setLiveObservation(result.status);
  };

  const state = snapshot?.state;
  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">XP</div>
          <div>
            <p>X-Poker AI Agent</p>
            <h1>Monitor</h1>
          </div>
        </div>
        <div className="topbar-status">
          <StatusPill tone={connection === "live" ? "ok" : "warn"}>{connection}</StatusPill>
          <StatusPill tone="danger">Control disabled</StatusPill>
          <span className="sequence">SEQ {snapshot?.sequence ?? 0}</span>
        </div>
      </header>

      <div className="dashboard-grid">
        <aside className="sidebar">
          <section className="panel setup-panel">
            <p className="eyebrow">Session setup</p>
            <h3>Table configuration</h3>
            <label>Players</label>
            <div className="segmented">
              {([6, 9] as const).map((size) => (
                <button className={tableSize === size ? "selected" : ""} key={size} onClick={() => setTableSize(size)}>
                  {size}-max
                </button>
              ))}
            </div>
            <label>Chip display</label>
            <div className="segmented">
              {(["BB", "native"] as const).map((mode) => (
                <button className={chipMode === mode ? "selected" : ""} key={mode} onClick={() => setChipMode(mode)}>
                  {mode === "BB" ? "Big blinds" : "Native chips"}
                </button>
              ))}
            </div>
            <label htmlFor="stack">Starting stack</label>
            <input id="stack" value={stackInput} onChange={(event) => setStackInput(event.target.value)} />
            {chipMode === "native" && (
              <>
                <label htmlFor="blind">Big blind in native chips</label>
                <input id="blind" value={bigBlindText} onChange={(event) => setBigBlindText(event.target.value)} />
              </>
            )}
            <button className="primary-button" onClick={() => void validateSession()}>Validate session</button>
            {session && (
              <div className="validation-card">
                <strong>{session.game_config_id}</strong>
                <span>{session.stack.display_text}</span>
                <small>{session.ready_for_strategy ? "BB normalization ready" : session.blocking_reason}</small>
              </div>
            )}
            {sessionError && <p className="error-copy">{sessionError}</p>}
          </section>

          <button className="capture-button" onClick={() => void inspectCapture()}>Inspect live X-Poker table</button>
          <div className="capture-controls">
            <button className="capture-button" disabled={liveObservation?.running} onClick={() => void startLiveCapture()}>Start continuous observation</button>
            <button className="secondary-button" disabled={!liveObservation?.running} onClick={() => void stopLiveCapture()}>Stop</button>
          </div>
          {captureError && <p className="error-copy sidebar-error">{captureError}</p>}
          {captureDiagnostic && <CapturePreview diagnostic={captureDiagnostic} nonce={captureNonce} />}

          <section className="panel health-panel">
            <p className="eyebrow">System health</p>
            <div className="health-row"><span>Source</span><strong>{snapshot?.source_mode.replaceAll("_", " ") ?? "loading"}</strong></div>
            <div className="health-row"><span>Capture</span><strong>{liveObservation?.running ? `Live · ${liveObservation.frames_succeeded} frames` : captureDiagnostic ? "Diagnostic ready" : "Inactive"}</strong></div>
            <div className="health-row"><span>Freshness</span><strong>{liveObservation?.latest_age_ms != null ? `${Math.round(liveObservation.latest_age_ms)} ms` : "—"}</strong></div>
            <div className="health-row"><span>Target</span><strong>{liveObservation?.target_stable === false ? "Changed · stopped" : liveObservation?.target_fingerprint ? "Stable" : "Waiting"}</strong></div>
            <div className="health-row"><span>Mode consensus</span><strong>{liveObservation?.mode_consensus.accepted ? `${liveObservation.mode_consensus.value} · ${liveObservation.mode_consensus.stable_frames}` : liveObservation?.mode_consensus.reason ?? "waiting"}</strong></div>
            <div className="health-row"><span>Pot consensus</span><strong>{liveObservation?.pot_consensus.accepted ? `${liveObservation.pot_consensus.value} · ${liveObservation.pot_consensus.stable_frames}` : liveObservation?.pot_consensus.reason ?? "waiting"}</strong></div>
            <div className="health-row"><span>Board consensus</span><strong>{liveObservation?.board_consensus.accepted ? `${liveObservation.board_consensus.value} cards` : liveObservation?.board_consensus.reason ?? "waiting"}</strong></div>
            <div className="health-row"><span>Recognized board</span><strong>{liveObservation?.board_cards_accepted ? liveObservation.recognized_board_cards.join(" ") : liveObservation?.board_cards_reason ?? "waiting"}</strong></div>
            <div className="health-row"><span>Dealer seat</span><strong>{liveObservation?.dealer_consensus.accepted ? liveObservation.dealer_consensus.value : liveObservation?.dealer_consensus.reason ?? "waiting"}</strong></div>
            <div className="health-row"><span>Active seats</span><strong>{liveObservation?.active_seats.length ?? 0}/{tableSize}</strong></div>
            <div className="health-row"><span>Position gate</span><strong>{liveObservation?.positions_reason ?? "waiting"}</strong></div>
            <div className="health-row"><span>Stable stacks</span><strong>{liveObservation?.seat_stack_consensus.filter((seat) => seat.consensus.accepted).length ?? 0}/{tableSize}</strong></div>
            <div className="health-row"><span>Stable action badges</span><strong>{liveObservation?.seat_action_consensus.filter((seat) => seat.consensus.accepted).length ?? 0}</strong></div>
            <div className="health-row"><span>Derived candidates</span><strong>{liveObservation?.derived_action_candidates.length ?? 0} · epoch {liveObservation?.hand_epoch ?? 0}</strong></div>
            <div className="health-row"><span>Stack deltas</span><strong>{liveObservation?.stack_delta_candidates.length ?? 0}</strong></div>
            <div className="health-row"><span>Amount matches</span><strong>{liveObservation?.action_amount_reconciliations.filter((item) => item.status === "matched").length ?? 0}</strong></div>
            <div className="health-row"><span>Strategy</span><strong>{snapshot?.health.strategy_status ?? "unavailable"}</strong></div>
            <div className="health-row"><span>Dropped UI updates</span><strong>{snapshot?.metrics.dropped_deliveries ?? 0}</strong></div>
            <div className="health-row"><span>Snapshot latency</span><strong>{snapshot ? `${snapshot.metrics.processing_latency_ms.toFixed(2)} ms` : "—"}</strong></div>
            {(error || snapshot?.health.warnings.length) && (
              <div className="warning-stack">
                {error && <p>{error}</p>}
                {snapshot?.health.warnings.map((warning) => <p key={warning}>{warning}</p>)}
              </div>
            )}
          </section>
        </aside>

        <div className="main-column">
          {state ? <TableCanvas state={state} chipMode={chipMode} bigBlindNative={bigBlindNative} /> : <section className="panel loading-panel">Loading replay state…</section>}
          <section className="panel replay-bar">
            <div>
              <p className="eyebrow">Replay transport</p>
              <strong>{snapshot?.replay.index ?? 0} / {snapshot?.replay.total ?? 14} transitions</strong>
            </div>
            <input
              aria-label="Replay transition"
              className="replay-slider"
              type="range"
              min="0"
              max={snapshot?.replay.total ?? 14}
              value={snapshot?.replay.index ?? 0}
              onChange={(event) => void seek(Number(event.target.value))}
            />
            <div className="button-row">
              <button className="secondary-button step-button" aria-label="Previous transition" onClick={() => void seek((snapshot?.replay.index ?? 0) - 1)}>‹</button>
              <button className="primary-button" onClick={() => void runReplay()}>Run replay</button>
              <button className="secondary-button step-button" aria-label="Next transition" onClick={() => void seek((snapshot?.replay.index ?? 0) + 1)}>›</button>
              <button className="secondary-button" onClick={() => void stopReplay()}>Stop</button>
            </div>
          </section>
          <div className="intel-grid">
            <RangeGrid matrix={matrix} loading={matrixLoading} />
            <section className="panel strategy-panel">
              <div className="panel-heading compact">
                <div><p className="eyebrow">Decision intelligence</p><h3>Strategy & exploit</h3></div>
                <StatusPill tone="warn">Unavailable</StatusPill>
              </div>
              <div className="strategy-block">
                <span>GTO match</span><strong>{String(snapshot?.strategy.status ?? "unavailable")}</strong>
                <small>No configuration-matched solver artifact is installed.</small>
              </div>
              <div className="strategy-block">
                <span>Reference prior</span><strong>{formatPercent(snapshot?.strategy.confidence)}</strong>
                <small>Visible for inspection, never substituted as exact GTO.</small>
              </div>
              <div className="strategy-block">
                <span>Exploit model</span><strong>{String(snapshot?.exploit.status ?? "synthetic_only")}</strong>
                <small>Waiting for reconstructed opponent observations.</small>
              </div>
              <div className="math-grid">
                <div><span>Effective</span><strong>{snapshot?.poker_math.effective_stack_bb ? `${snapshot.poker_math.effective_stack_bb}BB` : "—"}</strong></div>
                <div><span>SPR</span><strong>{snapshot?.poker_math.spr ? Number(snapshot.poker_math.spr).toFixed(2) : "—"}</strong></div>
                <div><span>Call</span><strong>{snapshot ? `${snapshot.poker_math.call_amount_bb}BB` : "—"}</strong></div>
                <div><span>Required equity</span><strong>{snapshot?.poker_math.pot_odds_required_equity ? formatPercent(Number(snapshot.poker_math.pot_odds_required_equity)) : "—"}</strong></div>
                <div><span>Equity</span><strong>{formatPercent(snapshot?.poker_math.equity)}</strong></div>
                <div><span>Call EV</span><strong>{snapshot?.poker_math.call_ev_bb ?? "—"}</strong></div>
              </div>
              <label htmlFor="position">Range position</label>
              <select id="position" value={position} onChange={(event) => setPosition(event.target.value)}>
                {POSITIONS[tableSize].map((item) => <option key={item}>{item}</option>)}
              </select>
            </section>
          </div>
        </div>

        <aside className="rightbar">
          <ActionHistory events={snapshot?.action_history ?? []} />
          <section className="panel audit-panel">
            <p className="eyebrow">Safety boundary</p>
            <h3>Decision audit</h3>
            <div className="audit-lock">LOCKED</div>
            <div className="audit-checks">
              {snapshot?.audit.map((item) => (
                <article key={item.check}>
                  <span className={item.status}>{item.status}</span>
                  <strong>{item.check.replaceAll("_", " ")}</strong>
                  <p>{item.detail}</p>
                  <small>{item.source}</small>
                </article>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </main>
  );
}
