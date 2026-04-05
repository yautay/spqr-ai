import { apiRequest } from "./httpClient";
import type {
  AIMoveResponsePayload,
  ActionResponsePayload,
  GameStatePayload,
  LegalMovesPayload,
  MissilePreviewResponsePayload,
  RulesetMode,
  RulesetsPayload,
  SnapshotListPayload,
  SnapshotPayload,
  ShockPreviewResponsePayload,
} from "@shared-schema/game";

export async function fetchGameState(): Promise<GameStatePayload> {
  return apiRequest<GameStatePayload>("/game/state");
}

export async function fetchRulesets(): Promise<RulesetsPayload> {
  return apiRequest<RulesetsPayload>("/game/rulesets");
}

export async function createNewGame(ruleset: RulesetMode): Promise<GameStatePayload> {
  return apiRequest<GameStatePayload>("/game/new", {
    method: "POST",
    body: JSON.stringify({ ruleset }),
  });
}

export async function saveGame(slotId: string): Promise<SnapshotPayload> {
  return apiRequest<SnapshotPayload>("/game/save", {
    method: "POST",
    body: JSON.stringify({ slot_id: slotId }),
  });
}

export async function loadGame(slotId: string): Promise<SnapshotPayload> {
  return apiRequest<SnapshotPayload>("/game/load", {
    method: "POST",
    body: JSON.stringify({ slot_id: slotId }),
  });
}

export async function fetchSnapshots(): Promise<SnapshotListPayload> {
  return apiRequest<SnapshotListPayload>("/game/saves");
}

export async function advanceActivationStep(): Promise<GameStatePayload> {
  return apiRequest<GameStatePayload>("/game/activation/advance", {
    method: "POST",
  });
}

export async function forceEndTurn(): Promise<GameStatePayload> {
  return apiRequest<GameStatePayload>("/game/end-turn", {
    method: "POST",
  });
}

export async function fetchLegalMoves(unitId: string): Promise<LegalMovesPayload> {
  return apiRequest<LegalMovesPayload>(`/game/legal-moves/${encodeURIComponent(unitId)}`);
}

export async function executeMove(unitId: string, destination: { q: number; r: number }): Promise<ActionResponsePayload> {
  return apiRequest<ActionResponsePayload>("/game/action", {
    method: "POST",
    body: JSON.stringify({
      unit_id: unitId,
      destination,
    }),
  });
}

export async function executeMissileAction(payload: {
  firing_unit_id: string;
  target_unit_id: string;
  modifier_ids?: string[];
  fire_mode?: "active" | "reaction";
  reaction_trigger?: "entry" | "retire" | "return";
}): Promise<ActionResponsePayload> {
  return apiRequest<ActionResponsePayload>("/game/action/missile", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function executeMissileReload(unitId: string): Promise<ActionResponsePayload> {
  return apiRequest<ActionResponsePayload>("/game/action/missile/reload", {
    method: "POST",
    body: JSON.stringify({ unit_id: unitId }),
  });
}

export async function executeShockAction(payload: {
  attacker_unit_id: string;
  defender_unit_id: string;
  angle?: "front" | "flank" | "rear";
  modifier_ids?: string[];
}): Promise<ActionResponsePayload> {
  return apiRequest<ActionResponsePayload>("/game/action/shock", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchMissilePreview(payload: {
  firing_unit_id: string;
  target_unit_id: string;
  modifier_ids?: string[];
  fire_mode?: "active" | "reaction";
  reaction_trigger?: "entry" | "retire" | "return";
}): Promise<MissilePreviewResponsePayload> {
  return apiRequest<MissilePreviewResponsePayload>("/game/preview/missile", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchShockPreview(payload: {
  attacker_unit_id: string;
  defender_unit_id: string;
  angle?: "front" | "flank" | "rear";
  modifier_ids?: string[];
}): Promise<ShockPreviewResponsePayload> {
  return apiRequest<ShockPreviewResponsePayload>("/game/preview/shock", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function requestAiMove(payload?: { time_budget_ms?: number; max_candidates?: number }): Promise<AIMoveResponsePayload> {
  return apiRequest<AIMoveResponsePayload>("/ai/move", {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });
}
