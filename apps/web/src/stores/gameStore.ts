import { computed, ref } from "vue";
import { defineStore } from "pinia";

import {
  createNewGame,
  executeMissileAction,
  executeMissileReload,
  executeMove,
  executeShockAction,
  fetchMissilePreview,
  fetchGameState,
  fetchLegalMoves,
  fetchRulesets,
  fetchShockPreview,
  requestAiMove,
  setTurnPhase,
} from "../api/gameApi";
import type {
  AIMoveResponsePayload,
  ActionResponsePayload,
  GameStatePayload,
  LegalMoveOptionPayload,
  MissilePreviewPayload,
  RulesetMode,
  ShockPreviewPayload,
  TurnPhase,
  UnitPayload,
} from "../types/game";

export const useGameStore = defineStore("game", () => {
  const state = ref<GameStatePayload | null>(null);
  const rulesets = ref<RulesetMode[]>([]);
  const legalMovesByUnit = ref<Record<string, LegalMoveOptionPayload[]>>({});
  const isLoading = ref(false);
  const isSubmitting = ref(false);
  const error = ref<string | null>(null);
  const lastActionResult = ref<ActionResponsePayload | null>(null);
  const missilePreview = ref<MissilePreviewPayload | null>(null);
  const shockPreview = ref<ShockPreviewPayload | null>(null);
  const missilePreviewReason = ref<string | null>(null);
  const shockPreviewReason = ref<string | null>(null);
  const lastAiMoveResponse = ref<AIMoveResponsePayload | null>(null);

  const unitsById = computed<Record<string, UnitPayload>>(() => {
    if (!state.value) {
      return {};
    }

    return Object.fromEntries(state.value.units.map((unit) => [unit.unit_id, unit]));
  });

  async function initialize(): Promise<void> {
    isLoading.value = true;
    error.value = null;
    try {
      const [rulesetsPayload, gameState] = await Promise.all([fetchRulesets(), fetchGameState()]);
      rulesets.value = rulesetsPayload.rulesets;
      state.value = gameState;
    } catch (caughtError) {
      error.value = caughtError instanceof Error ? caughtError.message : "Failed to initialize game state.";
    } finally {
      isLoading.value = false;
    }
  }

  async function refreshState(): Promise<void> {
    isLoading.value = true;
    error.value = null;
    try {
      state.value = await fetchGameState();
    } catch (caughtError) {
      error.value = caughtError instanceof Error ? caughtError.message : "Failed to refresh game state.";
    } finally {
      isLoading.value = false;
    }
  }

  async function startNewGame(ruleset: RulesetMode): Promise<void> {
    isSubmitting.value = true;
    error.value = null;
    try {
      state.value = await createNewGame(ruleset);
      legalMovesByUnit.value = {};
      lastActionResult.value = null;
      lastAiMoveResponse.value = null;
      clearCombatPreviews();
    } catch (caughtError) {
      error.value = caughtError instanceof Error ? caughtError.message : "Failed to create a new game.";
    } finally {
      isSubmitting.value = false;
    }
  }

  async function changePhase(phase: TurnPhase): Promise<void> {
    isSubmitting.value = true;
    error.value = null;
    try {
      state.value = await setTurnPhase(phase);
    } catch (caughtError) {
      error.value = caughtError instanceof Error ? caughtError.message : "Failed to change phase.";
    } finally {
      isSubmitting.value = false;
    }
  }

  async function loadLegalMoves(unitId: string): Promise<LegalMoveOptionPayload[]> {
    error.value = null;
    try {
      const payload = await fetchLegalMoves(unitId);
      legalMovesByUnit.value = {
        ...legalMovesByUnit.value,
        [unitId]: payload.options,
      };
      return payload.options;
    } catch (caughtError) {
      error.value = caughtError instanceof Error ? caughtError.message : "Failed to load legal moves.";
      return [];
    }
  }

  async function loadMissilePreview(payload: {
    firing_unit_id: string;
    target_unit_id: string;
    modifier_ids?: string[];
    fire_mode?: "active" | "reaction";
    reaction_trigger?: "entry" | "retire" | "return";
  }): Promise<void> {
    try {
      const response = await fetchMissilePreview(payload);
      missilePreview.value = response.preview;
      missilePreviewReason.value = response.reason;
    } catch (caughtError) {
      missilePreview.value = null;
      missilePreviewReason.value = caughtError instanceof Error ? caughtError.message : "missile_preview_failed";
    }
  }

  async function loadShockPreview(payload: {
    attacker_unit_id: string;
    defender_unit_id: string;
    angle?: "front" | "flank" | "rear";
    modifier_ids?: string[];
  }): Promise<void> {
    try {
      const response = await fetchShockPreview(payload);
      shockPreview.value = response.preview;
      shockPreviewReason.value = response.reason;
    } catch (caughtError) {
      shockPreview.value = null;
      shockPreviewReason.value = caughtError instanceof Error ? caughtError.message : "shock_preview_failed";
    }
  }

  function clearCombatPreviews(): void {
    missilePreview.value = null;
    shockPreview.value = null;
    missilePreviewReason.value = null;
    shockPreviewReason.value = null;
  }

  async function runAiMove(payload?: { time_budget_ms?: number; max_candidates?: number }): Promise<AIMoveResponsePayload | null> {
    isSubmitting.value = true;
    error.value = null;
    try {
      const response = await requestAiMove(payload);
      lastAiMoveResponse.value = response;
      if (response.action_result) {
        state.value = response.action_result.state;
        lastActionResult.value = response.action_result;
      }
      legalMovesByUnit.value = {};
      clearCombatPreviews();
      return response;
    } catch (caughtError) {
      error.value = caughtError instanceof Error ? caughtError.message : "AI move request failed.";
      return null;
    } finally {
      isSubmitting.value = false;
    }
  }

  function clearLegalMoves(unitId?: string): void {
    if (!unitId) {
      legalMovesByUnit.value = {};
      return;
    }

    const next = { ...legalMovesByUnit.value };
    delete next[unitId];
    legalMovesByUnit.value = next;
  }

  async function moveUnit(unitId: string, destination: { q: number; r: number }): Promise<ActionResponsePayload | null> {
    return runAction(async () => executeMove(unitId, destination));
  }

  async function fireMissile(payload: {
    firing_unit_id: string;
    target_unit_id: string;
    modifier_ids?: string[];
    fire_mode?: "active" | "reaction";
    reaction_trigger?: "entry" | "retire" | "return";
  }): Promise<ActionResponsePayload | null> {
    return runAction(async () => executeMissileAction(payload));
  }

  async function reloadMissile(unitId: string): Promise<ActionResponsePayload | null> {
    return runAction(async () => executeMissileReload(unitId));
  }

  async function resolveShock(payload: {
    attacker_unit_id: string;
    defender_unit_id: string;
    angle?: "front" | "flank" | "rear";
    modifier_ids?: string[];
  }): Promise<ActionResponsePayload | null> {
    return runAction(async () => executeShockAction(payload));
  }

  function clearError(): void {
    error.value = null;
  }

  async function runAction(action: () => Promise<ActionResponsePayload>): Promise<ActionResponsePayload | null> {
    isSubmitting.value = true;
    error.value = null;

    try {
      const result = await action();
      state.value = result.state;
      lastActionResult.value = result;
      legalMovesByUnit.value = {};
      clearCombatPreviews();
      return result;
    } catch (caughtError) {
      error.value = caughtError instanceof Error ? caughtError.message : "Action request failed.";
      return null;
    } finally {
      isSubmitting.value = false;
    }
  }

  return {
    state,
    rulesets,
    legalMovesByUnit,
    isLoading,
    isSubmitting,
    error,
    lastActionResult,
    missilePreview,
    shockPreview,
    missilePreviewReason,
    shockPreviewReason,
    lastAiMoveResponse,
    unitsById,
    initialize,
    refreshState,
    startNewGame,
    changePhase,
    loadLegalMoves,
    loadMissilePreview,
    loadShockPreview,
    clearCombatPreviews,
    runAiMove,
    clearLegalMoves,
    moveUnit,
    fireMissile,
    reloadMissile,
    resolveShock,
    clearError,
  };
});
