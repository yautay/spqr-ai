import { apiRequest } from "./httpClient";
import type { ActionResponsePayload, GameStatePayload, LegalMovesPayload, RulesetMode, RulesetsPayload, TurnPhase } from "../types/game";

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

export async function setTurnPhase(phase: TurnPhase): Promise<GameStatePayload> {
  return apiRequest<GameStatePayload>("/game/phase", {
    method: "POST",
    body: JSON.stringify({ phase }),
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
