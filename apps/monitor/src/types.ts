export type TableSize = 9;

export interface LiveHeroCalculation {
  hero_seat: number | null;
  hero_seat_confidence: number;
  hero_position: string | null;
  dealt_player_count: number;
  range_seat_mismatch: number;
  cards: string[];
  hand_class: string | null;
  hero_stack_chips: string | null;
  pot_chips: string | null;
  call_amount_chips: string | null;
  effective_stack_chips: string | null;
  required_equity: string | null;
  spr: string | null;
  ready: boolean;
  issues: string[];
  assumptions: string[];
}

export interface SeatState {
  seat: number;
  position: string | null;
  participation: string;
  starting_stack_chips: string;
  stack_chips: string;
  committed_by_street_chips: Record<string, string>;
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
  pot_main_chips: string;
  current_bet_chips: string;
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
  amount: { to_chips: string | null; added_chips: string } | null;
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
  poker_math: {
    effective_stack_chips: string | null;
    call_amount_chips: string;
    pot_odds_required_equity: string | null;
    spr: string | null;
    equity: number | null;
    call_ev_chips: string | null;
    status: string;
    assumptions: string[];
  };
  strategy: {
    status: "exact" | "abstracted" | "unavailable";
    role: "gto_solution" | "reference_prior" | "none";
    confidence: number;
    source_artifact_id: string | null;
    mismatch: Record<string, unknown>;
    assumptions: string[];
  };
  exploit: {
    status: "available" | "synthetic_only" | "unavailable";
    confidence: number;
    sample_size: number;
    assumptions: string[];
  };
  audit: Array<{ check: string; status: string; detail: string; source: string }>;
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
  possible_combos: number;
  included_combos: number;
  combo_weight: number;
  inclusion_frequency: number;
  action_mix: Record<string, number>;
  unassigned_action_frequency: number;
  equity: number | null;
  ev_chips: Record<string, number>;
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
    display_text: string;
    amount_chips: string;
  };
  native_small_blind: "1";
  native_big_blind: "2";
}

export interface LiveCaptureDiagnostic {
  schema_version: "1.0";
  captured_at: string;
  frame_sequence: number;
  content_sha256: string;
  layout_id: string;
  table_size: TableSize;
  frame_width: number;
  frame_height: number;
  target_hwnd: number;
  target_process_id: number;
  target_fingerprint: string;
  capture_latency_ms: number;
  ocr_latency_ms: number;
  visual_role_confidence: number;
  current_hand_supported: boolean;
  current_hand_mode: "standard_nlh" | "single_board_bomb_pot" | "ambiguous";
  standard_nlh_supported: boolean;
  single_board_bomb_pot_supported: boolean;
  bomb_pot_state: "none" | "scheduled" | "active" | "ambiguous";
  hands_until_bomb: number | null;
  bomb_pot_interval_hands: number | null;
  bomb_pot_forced_contribution_native: string | null;
  special_rule: "bomb_pot" | null;
  rule_confidence: number;
  mode_reason: string;
  matched_signals: string[];
  rule_text: string;
  pot_text: string;
  pot: {
    value_native: string | null;
    token: string | null;
    confidence: number;
    accepted: false;
    reason: string;
  };
  board_rows: number;
  board_card_slots: number;
  board_geometry_supported: boolean;
  board_geometry_confidence: number;
  board_geometry_reasons: string[];
  board_cards: Array<{
    card: string | null;
    confidence: number;
    rank_distance: number;
    rank_margin: number;
    accepted: false;
    reason: string;
  }>;
  dealer: {
    seat: number | null;
    confidence: number;
    box: { left: number; top: number; right: number; bottom: number } | null;
    accepted: false;
    reason: string;
  };
  regions: Record<string, [number, number, number, number]>;
  seat_observations: Array<{
    seat: number;
    status: "occupied" | "empty" | "ambiguous";
    confidence: number;
    dark_panel_fraction: number;
    plus_horizontal_pixels: number;
    plus_vertical_pixels: number;
  }>;
  seat_panels: Array<{
    seat: number;
    status: "empty" | "seated" | "on_break" | "ambiguous";
    stack_native: string | null;
    stack_token: string | null;
    confidence: number;
    accepted: false;
    ocr_text_sha256: string | null;
    reason: string;
  }>;
  seat_actions: Array<{
    seat: number;
    action: "fold" | "check" | "call" | "bet" | "raise" | "all_in" | null;
    confidence: number;
    accepted: false;
    ocr_text_sha256: string | null;
    reason: string;
  }>;
}

export interface LiveObservationStatus {
  schema_version: "1.0";
  running: boolean;
  table_size: TableSize;
  interval_ms: number;
  started_at: string | null;
  stopped_at: string | null;
  latest_sequence: number;
  frames_attempted: number;
  frames_succeeded: number;
  frames_failed: number;
  consecutive_failures: number;
  latest_captured_at: string | null;
  latest_age_ms: number | null;
  target_fingerprint: string | null;
  target_stable: boolean;
  current_hand_mode: "standard_nlh" | "single_board_bomb_pot" | "ambiguous";
  current_hand_supported: boolean;
  mode_consensus: {
    accepted: boolean;
    value: string | null;
    confidence: number;
    stable_frames: number;
    alternatives: string[];
    reason: string | null;
  };
  epoch_mode_consensus: {
    accepted: boolean;
    value: string | null;
    confidence: number;
    stable_frames: number;
    alternatives: string[];
    reason: string | null;
  };
  blind_consensus: {
    accepted: boolean;
    value: string | null;
    confidence: number;
    stable_frames: number;
    alternatives: string[];
    reason: string | null;
  };
  session_blind_consensus: {
    accepted: boolean;
    value: string | null;
    confidence: number;
    stable_frames: number;
    alternatives: string[];
    reason: string | null;
  };
  board_consensus: {
    accepted: boolean;
    value: string | null;
    confidence: number;
    stable_frames: number;
    alternatives: string[];
    reason: string | null;
  };
  board_card_consensus: Array<{
    accepted: boolean;
    value: string | null;
    confidence: number;
    stable_frames: number;
    alternatives: string[];
    reason: string | null;
  }>;
  recognized_board_cards: string[];
  board_cards_accepted: boolean;
  board_cards_reason: string;
  hero_card_consensus: Array<{
    accepted: boolean;
    value: string | null;
    confidence: number;
    stable_frames: number;
    alternatives: string[];
    reason: string | null;
  }>;
  recognized_hero_cards: string[];
  hero_cards_accepted: boolean;
  hero_cards_reason: string;
  detected_hero_seat: number | null;
  hero_seat_confidence: number;
  hero_seat_reason: string;
  detected_hero_position: string | null;
  dealer_consensus: {
    accepted: boolean;
    value: string | null;
    confidence: number;
    stable_frames: number;
    alternatives: string[];
    reason: string | null;
  };
  seat_status_consensus: Array<{
    seat: number;
    consensus: {
      accepted: boolean;
      value: string | null;
      confidence: number;
      stable_frames: number;
      alternatives: string[];
      reason: string | null;
    };
  }>;
  active_seats: number[];
  provisional_positions: Record<string, string>;
  positions_reason: string;
  pot_consensus: {
    accepted: boolean;
    value: string | null;
    confidence: number;
    stable_frames: number;
    alternatives: string[];
    reason: string | null;
  };
  seat_stack_consensus: Array<{
    seat: number;
    player_status: "empty" | "seated" | "on_break" | "ambiguous";
    consensus: {
      accepted: boolean;
      value: string | null;
      confidence: number;
      stable_frames: number;
      alternatives: string[];
      reason: string | null;
    };
  }>;
  seat_action_consensus: Array<{
    seat: number;
    consensus: {
      accepted: boolean;
      value: string | null;
      confidence: number;
      stable_frames: number;
      alternatives: string[];
      reason: string | null;
    };
  }>;
  hero_control_consensus: {
    accepted: boolean;
    value: string | null;
    confidence: number;
    stable_frames: number;
    alternatives: string[];
    reason: string | null;
  };
  hand_epoch: number;
  hand_boundary_validation: {
    hand_epoch: number;
    previous_dealer_seat: number | null;
    current_dealer_seat: number | null;
    expected_dealer_seat: number | null;
    previous_active_seats: number[];
    current_active_seats: number[];
    status: "pending" | "validated" | "rejected";
    issues: string[];
    canonical_event_accepted: false;
    reason: string;
  };
  blind_post_reconciliations: Array<{
    hand_epoch: number;
    seat: number;
    blind_kind: "small_blind" | "big_blind";
    amount_native: string;
    stack_delta_event_id: string | null;
    badge_amount_event_id: string | null;
    status: "matched" | "pending" | "ambiguous";
    canonical_event_accepted: false;
    reason: string;
  }>;
  hand_starting_stacks_native: Record<string, string>;
  reconstruction_readiness: {
    hand_epoch: number;
    ready: boolean;
    big_blind_native: string | null;
    eligible_action_event_ids: string[];
    issues: string[];
    canonical_events_emitted: boolean;
    reason: string;
  };
  canonical_hand: {
    hand_epoch: number;
    hand_id: string;
    events: Array<Record<string, unknown>>;
    state: Record<string, unknown>;
    source_action_event_ids: string[];
    complete: false;
    reason: string;
  } | null;
  canonical_reconstruction_error: string | null;
  derived_action_candidates: Array<{
    event_id: string;
    hand_epoch: number;
    frame_sequence: number;
    seat: number;
    street: "preflop" | "flop" | "turn" | "river";
    action: "fold" | "check" | "call" | "bet" | "raise" | "all_in";
    confidence: number;
    occurrence: number;
    dealer_seat: number | null;
    active_seats: number[];
    canonical_event_accepted: false;
    reason: string;
  }>;
  seat_badge_amount_candidates: Array<{
    event_id: string;
    hand_epoch: number;
    frame_sequence: number;
    seat: number;
    amount_native: string;
    confidence: number;
    canonical_event_accepted: false;
    reason: string;
  }>;
  stack_delta_candidates: Array<{
    event_id: string;
    hand_epoch: number;
    frame_sequence: number;
    seat: number;
    street: "preflop" | "flop" | "turn" | "river" | "unknown";
    previous_stack_native: string;
    current_stack_native: string;
    committed_native: string;
    canonical_event_accepted: false;
    reason: string;
  }>;
  pot_delta_candidates: Array<{
    event_id: string;
    hand_epoch: number;
    frame_sequence: number;
    street: "preflop" | "flop" | "turn" | "river" | "unknown";
    previous_pot_native: string;
    current_pot_native: string;
    increase_native: string;
    evidence_mode: "stable_endpoints" | "cross_signal_single_frame";
    confidence: number;
    canonical_event_accepted: false;
    reason: string;
  }>;
  action_amount_reconciliations: Array<{
    action_event_id: string;
    delta_event_id: string | null;
    seat: number;
    action: "fold" | "check" | "call" | "bet" | "raise" | "all_in";
    amount_native: string | null;
    status: "not_required" | "matched" | "pending" | "ambiguous";
    canonical_event_accepted: false;
    reason: string;
  }>;
  action_order_validations: Array<{
    hand_epoch: number;
    street: "preflop" | "flop" | "turn" | "river";
    action_event_ids: string[];
    observed_seats: number[];
    expected_start_seat: number | null;
    expected_next_seat: number | null;
    status: "prefix_consistent" | "pending" | "inconsistent";
    issues: string[];
    canonical_event_accepted: false;
    reason: string;
  }>;
  action_pot_reconciliations: Array<{
    action_event_id: string;
    stack_delta_event_id: string | null;
    pot_delta_event_id: string | null;
    seat: number;
    action: "fold" | "check" | "call" | "bet" | "raise" | "all_in";
    amount_native: string | null;
    status: "not_required" | "matched" | "pending" | "ambiguous" | "mismatch";
    canonical_event_accepted: false;
    reason: string;
  }>;
  last_error: string | null;
  controller_enabled: false;
}
