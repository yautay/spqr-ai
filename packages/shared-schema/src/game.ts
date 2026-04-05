export type RulesetMode = "original" | "simple";
export type Side = "red" | "blue";
export type TurnPhase = "orders" | "rout_and_reload";
export type MissileSupply = "normal" | "low" | "no";
export type ReactionTrigger = "entry" | "retire" | "return";

export interface HexPayload {
  q: number;
  r: number;
}

export interface TilePayload {
  coord: HexPayload;
  terrain: string;
  move_cost: number;
  passable: boolean;
}

export interface UnitPayload {
  unit_id: string;
  side: Side;
  position: HexPayload;
  move_allowance: number;
  tq: number;
  cohesion_hits: number;
  is_routed: boolean;
  exerts_zoc: boolean;
  move_profile_id: string | null;
  stacking_category: string;
  missile_class_id: string | null;
  missile_supply: MissileSupply;
  shock_type: string;
  pursuit_capable: boolean;
}

export interface GameStatePayload {
  ruleset: RulesetMode;
  turn_number: number;
  turn_phase: TurnPhase;
  tiles: TilePayload[];
  active_side: Side;
  units: UnitPayload[];
}

export interface RulesetsPayload {
  rulesets: RulesetMode[];
}

export interface SnapshotSummaryPayload {
  slot_id: string;
  saved_at: string;
  event_offset: number;
}

export interface SnapshotPayload {
  slot_id: string;
  saved_at: string;
  event_offset: number;
  state: GameStatePayload;
}

export interface SnapshotListPayload {
  snapshots: SnapshotSummaryPayload[];
}

export interface ReplayStatePayload {
  total_events: number;
  state: GameStatePayload;
}

export interface ReplayVerificationPayload {
  ok: boolean;
  reason: string;
  total_events: number;
  replay_state_hash: string;
  current_state_hash: string;
}

export interface GameEventPayload {
  event_id: string;
  timestamp: string;
  event_type:
    | "game_reset"
    | "game_saved"
    | "game_loaded"
    | "activation_advanced"
    | "turn_ended"
    | "move_resolved"
    | "missile_resolved"
    | "reload_resolved"
    | "shock_resolved"
    | "ai_thinking"
    | "ai_move_selected";
  ok: boolean | null;
  reason: string | null;
  details: Record<string, string | number | boolean | null>;
}

export interface ActionResponsePayload {
  ok: boolean;
  reason: string;
  state: GameStatePayload;
  effects: StackingEffectPayload[];
  pending_tq_checks: PendingTQCheckPayload[];
  tq_check_outcomes: TQCheckOutcomePayload[];
  missile_outcome: MissileOutcomePayload | null;
  shock_outcome: ShockOutcomePayload | null;
  morale_outcomes: MoraleOutcomePayload[];
  pursuit_outcome: PursuitOutcomePayload | null;
  events: DomainEventPayload[];
}

export interface LegalMoveOptionPayload {
  destination: HexPayload;
  total_cost: number;
  path: HexPayload[];
}

export interface LegalMovesPayload {
  unit_id: string;
  options: LegalMoveOptionPayload[];
}

export interface StackingEffectPayload {
  effect_type: string;
  interaction: string;
  location: HexPayload;
  moving_unit_id: string;
  stationary_unit_id: string;
  moving_unit_cohesion_hits: number;
  stationary_unit_cohesion_hits: number;
  stationary_unit_tq_check_required: boolean;
  stationary_unit_tq_check_formula: string | null;
  tq_check_drm: number | null;
}

export interface PendingTQCheckPayload {
  unit_id: string;
  location: HexPayload;
  source: string;
  required: boolean;
  formula: string | null;
  drm: number | null;
  target: number;
}

export interface TQCheckOutcomePayload {
  unit_id: string;
  location: HexPayload;
  source: string;
  required: boolean;
  formula: string | null;
  drm: number | null;
  target: number;
  roll: number;
  passed: boolean;
  applied_cohesion_hits: number;
  became_routed: boolean;
}

export interface MissileDRMModifierPayload {
  id: string;
  drm: number;
}

export interface MissileOutcomePayload {
  firing_unit_id: string;
  target_unit_id: string;
  fire_mode: "active" | "reaction";
  reaction_trigger: ReactionTrigger | null;
  missile_class_id: string;
  range_to_target: number;
  table_strength: number;
  base_roll: number;
  total_drm: number;
  modified_roll: number;
  hit: boolean;
  applied_cohesion_hits: number;
  drm_breakdown: MissileDRMModifierPayload[];
}

export interface MissilePreviewPayload {
  firing_unit_id: string;
  target_unit_id: string;
  fire_mode: "active" | "reaction";
  reaction_trigger: ReactionTrigger | null;
  missile_class_id: string;
  range_to_target: number;
  table_strength: number;
  total_drm: number;
  hit_threshold: number;
  drm_breakdown: MissileDRMModifierPayload[];
}

export interface MissilePreviewResponsePayload {
  ok: boolean;
  reason: string;
  preview: MissilePreviewPayload | null;
}

export interface DomainEventPayload {
  event_type: string;
  details: Record<string, string | number | boolean | null>;
}

export interface ShockModifierPayload {
  id: string;
  shift: number;
}

export interface ShockOutcomePayload {
  attacker_unit_id: string;
  defender_unit_id: string;
  angle: "front" | "flank" | "rear";
  attacker_type: string;
  defender_type: string;
  base_column: number;
  total_shift: number;
  final_column: number;
  roll: number;
  attacker_hits: number;
  defender_hits: number;
  modifier_breakdown: ShockModifierPayload[];
}

export interface ShockPreviewPayload {
  attacker_unit_id: string;
  defender_unit_id: string;
  angle: "front" | "flank" | "rear";
  attacker_type: string;
  defender_type: string;
  base_column: number;
  total_shift: number;
  final_column: number;
  modifier_breakdown: ShockModifierPayload[];
}

export interface ShockPreviewResponsePayload {
  ok: boolean;
  reason: string;
  preview: ShockPreviewPayload | null;
}

export interface AIActionDescriptorPayload {
  action_type: "move" | "missile" | "reload" | "shock";
  summary: string;
  unit_id: string | null;
  destination: HexPayload | null;
  firing_unit_id: string | null;
  target_unit_id: string | null;
  attacker_unit_id: string | null;
  defender_unit_id: string | null;
  angle: "front" | "flank" | "rear" | null;
}

export interface AICandidateScorePayload {
  action_type: "move" | "missile" | "reload" | "shock";
  summary: string;
  score: number;
}

export interface AIMoveResponsePayload {
  ok: boolean;
  reason: string;
  considered_actions: number;
  elapsed_ms: number;
  selected_action: AIActionDescriptorPayload | null;
  top_candidates: AICandidateScorePayload[];
  action_result: ActionResponsePayload | null;
}

export interface MoraleOutcomePayload {
  unit_id: string;
  source: "shock";
  target: number;
  roll: number;
  passed: boolean;
  became_routed: boolean;
  retreated: boolean;
  eliminated: boolean;
}

export interface PursuitOutcomePayload {
  unit_id: string;
  destination: HexPayload;
}
