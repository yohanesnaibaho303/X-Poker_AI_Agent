export type TableSize = 6 | 9;
export type ChipMode = "BB" | "native";

export interface SeatState {
  seat: number;
  position: string | null;
  participation: string;
  starting_stack_bb: string;
  stack_bb: string;
  committed_by_street_bb: Record<string, string>;
  cards: string[];
}

export interface HandState {
  state_id: string;
  hand_id: string;
  revision: number;
  table_size: TableSize;
  table_status: string;
  street: string;
  dealer_seat: number | null;
  hero_seat: number;
  hero_position: string | null;
  hero_cards: string[];
  board: string[];
  seats: SeatState[];
  pot_main_bb: string;
  current_bet_bb: string;
  next_to_act_seat: number | null;
  available_actions: string[];
  validation: { legal: boolean; issues: string[] };
}

export interface HandEvent {
  event_id: string;
  sequence: number;
  category: string;
  type: string;
  actor_seat: number | null;
  street: string;
  amount: { to_bb: string | null; added_bb: string } | null;
  cards: string[];
  confidence: { score: number; calibration_id: string; stable_frames: number };
}

export interface MonitorSnapshot {
  schema_version: "1.0";
  sequence: number;
  generated_at: string;
  table_size: TableSize;
  source_mode: "synthetic_replay" | "recorded_replay" | "authorized_live";
  state: HandState;
  action_history: HandEvent[];
  health: {
    status: "ok" | "degraded" | "stopped";
    mode: string;
    capture_active: boolean;
    controller_enabled: false;
    strategy_status: "exact" | "abstracted" | "unavailable";
    warnings: string[];
  };
  metrics: {
    frames_processed: number;
    state_revision: number;
    event_count: number;
    stream_sequence: number;
    dropped_deliveries: number;
    processing_latency_ms: number;
  };
  replay: { active: boolean; index: number; total: number; interval_ms: number };
  strategy: Record<string, unknown>;
  exploit: Record<string, unknown>;
  audit: Array<Record<string, unknown>>;
}

export interface MonitorEnvelope {
  schema_version: "1.0";
  sequence: number;
  kind: "snapshot" | "state" | "event" | "health" | "heartbeat";
  payload: Record<string, unknown>;
}

export interface RangeCell {
  hand_class: string;
  row: number;
  column: number;
  inclusion_frequency: number;
  action_mix: Record<string, number>;
}

export interface RangeMatrix {
  player_ref: string;
  spot_key: string;
  cells: RangeCell[];
  source: Record<string, unknown>;
  confidence: number;
  version: string;
}

export interface SessionPreview {
  table_size: TableSize;
  game_config_id: string;
  stack: {
    display_mode: ChipMode;
    display_text: string;
    amount_bb: string | null;
    exact_native_chips: string | null;
  };
  ready_for_strategy: boolean;
  blocking_reason: string | null;
}
