<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import GameBoard from "./components/map/GameBoard.vue";
import ActionPreviewPanel from "./components/panels/ActionPreviewPanel.vue";
import EventLogPanel from "./components/panels/EventLogPanel.vue";
import UnitDetailsPanel from "./components/panels/UnitDetailsPanel.vue";
import { useGameStore } from "./stores/gameStore";
import { useLogStore } from "./stores/logStore";
import { useUiStore } from "./stores/uiStore";
import type { HexPayload, RulesetMode, TurnPhase } from "./types/game";

const gameStore = useGameStore();
const logStore = useLogStore();
const uiStore = useUiStore();
const selectedRuleset = ref<RulesetMode>("original");
const selectedPhase = ref<TurnPhase>("orders");

const boardState = computed(() => gameStore.state);
const availableRulesets = computed(() => gameStore.rulesets);
const selectedUnit = computed(() => {
  if (!uiStore.selectedUnitId) {
    return null;
  }

  return gameStore.unitsById[uiStore.selectedUnitId] ?? null;
});
const selectedUnitLegalMoves = computed(() => {
  if (!uiStore.selectedUnitId) {
    return [];
  }

  return gameStore.legalMovesByUnit[uiStore.selectedUnitId] ?? [];
});
const hoveredUnit = computed(() => {
  if (!uiStore.hoveredUnitId) {
    return null;
  }

  return gameStore.unitsById[uiStore.hoveredUnitId] ?? null;
});
const hoveredTargetUnit = computed(() => {
  if (!selectedUnit.value || !hoveredUnit.value || selectedUnit.value.side === hoveredUnit.value.side) {
    return null;
  }

  return hoveredUnit.value;
});
const movePreview = computed(() => {
  const coord = uiStore.selectedDestination ?? uiStore.hoveredHex;
  if (!coord) {
    return null;
  }

  return (
    selectedUnitLegalMoves.value.find(
      (option) => option.destination.q === coord.q && option.destination.r === coord.r
    ) ?? null
  );
});

onMounted(async () => {
  await gameStore.initialize();
  if (gameStore.state) {
    selectedPhase.value = gameStore.state.turn_phase;
  }
  logStore.append("info", "Session started", "Game state loaded from API.");
});

watch(
  availableRulesets,
  (rulesets) => {
    if (rulesets.length > 0 && !rulesets.includes(selectedRuleset.value)) {
      selectedRuleset.value = rulesets[0];
    }
  },
  { immediate: true }
);

watch(
  () => uiStore.selectedUnitId,
  async (unitId) => {
    uiStore.setSelectedDestination(null);
    if (!unitId) {
      gameStore.clearLegalMoves();
      return;
    }

    const unit = gameStore.unitsById[unitId];
    if (!unit || unit.side !== boardState.value?.active_side) {
      gameStore.clearLegalMoves(unitId);
      return;
    }

    await gameStore.loadLegalMoves(unitId);
  }
);

watch(
  () => boardState.value?.turn_phase,
  (phase) => {
    if (phase) {
      selectedPhase.value = phase;
    }
  },
  { immediate: true }
);

async function handleNewGame(): Promise<void> {
  await gameStore.startNewGame(selectedRuleset.value);
  uiStore.resetSelections();
  logStore.append("info", "New game", `Created ${selectedRuleset.value} ruleset match.`);
}

function handleUnitClick(unitId: string): void {
  if (uiStore.selectedUnitId === unitId) {
    uiStore.setSelectedUnit(null);
    return;
  }

  uiStore.setSelectedUnit(unitId);
}

function handleUnitHover(unitId: string | null): void {
  uiStore.setHoveredUnit(unitId);
}

function handleHexHover(coord: { q: number; r: number } | null): void {
  uiStore.setHoveredHex(coord);
}

async function handleHexClick(coord: HexPayload): Promise<void> {
  if (!uiStore.selectedUnitId) {
    return;
  }

  const destinationOption = selectedUnitLegalMoves.value.find(
    (option) => option.destination.q === coord.q && option.destination.r === coord.r
  );
  if (!destinationOption) {
    return;
  }

  uiStore.setSelectedDestination(coord);
  const result = await gameStore.moveUnit(uiStore.selectedUnitId, coord);
  if (!result) {
    logStore.append("error", "Move error", gameStore.error ?? "Move request failed.");
    return;
  }

  logStore.appendActionResult("move", result);
  if (!result.ok) {
    return;
  }

  uiStore.setSelectedDestination(null);
  await gameStore.loadLegalMoves(uiStore.selectedUnitId);
}

async function handleFireMissile(): Promise<void> {
  if (!selectedUnit.value || !hoveredTargetUnit.value) {
    return;
  }

  const result = await gameStore.fireMissile({
    firing_unit_id: selectedUnit.value.unit_id,
    target_unit_id: hoveredTargetUnit.value.unit_id,
    fire_mode: "active",
  });
  if (!result) {
    logStore.append("error", "Missile error", gameStore.error ?? "Missile request failed.");
    return;
  }

  logStore.appendActionResult("missile", result);
}

async function handleResolveShock(): Promise<void> {
  if (!selectedUnit.value || !hoveredTargetUnit.value) {
    return;
  }

  const result = await gameStore.resolveShock({
    attacker_unit_id: selectedUnit.value.unit_id,
    defender_unit_id: hoveredTargetUnit.value.unit_id,
    angle: "front",
  });
  if (!result) {
    logStore.append("error", "Shock error", gameStore.error ?? "Shock request failed.");
    return;
  }

  logStore.appendActionResult("shock", result);
}

async function handleReloadMissile(): Promise<void> {
  if (!selectedUnit.value) {
    return;
  }

  const result = await gameStore.reloadMissile(selectedUnit.value.unit_id);
  if (!result) {
    logStore.append("error", "Reload error", gameStore.error ?? "Reload request failed.");
    return;
  }

  logStore.appendActionResult("reload", result);
}

async function handleSetPhase(): Promise<void> {
  await gameStore.changePhase(selectedPhase.value);
  if (gameStore.error) {
    logStore.append("error", "Phase change failed", gameStore.error);
    return;
  }

  logStore.append("info", "Phase updated", `Turn phase set to ${selectedPhase.value}.`);
}
</script>

<template>
  <main class="layout">
    <header class="topbar">
      <div>
        <h1>Legions</h1>
        <p class="subtitle">Milestone 3 - Playable UI Slice</p>
      </div>
      <div class="topbar-actions">
        <select v-model="selectedRuleset" :disabled="gameStore.isSubmitting" class="ruleset-select">
          <option v-for="ruleset in availableRulesets" :key="ruleset" :value="ruleset">
            {{ ruleset }}
          </option>
        </select>
        <select v-model="selectedPhase" :disabled="gameStore.isSubmitting" class="ruleset-select">
          <option value="orders">orders</option>
          <option value="rout_and_reload">rout_and_reload</option>
        </select>
        <button type="button" class="action-button" :disabled="gameStore.isSubmitting" @click="handleSetPhase">
          Set Phase
        </button>
        <button type="button" class="action-button" :disabled="gameStore.isSubmitting" @click="handleNewGame">
          New Game
        </button>
      </div>
    </header>

    <section class="content-layout">
      <p v-if="gameStore.isLoading" class="status">Loading game state...</p>
      <p v-else-if="gameStore.error" class="status error">{{ gameStore.error }}</p>
      <template v-else>
        <aside class="side-panel">
          <UnitDetailsPanel
            :selected-unit="selectedUnit"
            :hovered-unit="hoveredUnit"
            :active-side="boardState?.active_side ?? null"
          />
          <ActionPreviewPanel
            :selected-unit="selectedUnit"
            :target-unit="hoveredTargetUnit"
            :move-preview="movePreview"
            :last-action-result="gameStore.lastActionResult"
            :is-submitting="gameStore.isSubmitting"
            @fire-missile="handleFireMissile"
            @resolve-shock="handleResolveShock"
            @reload-missile="handleReloadMissile"
          />
        </aside>
        <div class="board-layout">
          <GameBoard
            :state="boardState"
            :selected-unit-id="uiStore.selectedUnitId"
            :hovered-unit-id="uiStore.hoveredUnitId"
            :hovered-hex="uiStore.hoveredHex"
            :legal-moves="selectedUnitLegalMoves"
            @unit-click="handleUnitClick"
            @unit-hover="handleUnitHover"
            @hex-click="handleHexClick"
            @hex-hover="handleHexHover"
          />
        </div>
        <aside class="log-panel">
          <EventLogPanel :entries="logStore.entries" />
        </aside>
      </template>
    </section>
  </main>
</template>

<style scoped>
.layout {
  min-height: 100dvh;
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(160deg, #f4e8cd 0%, #e9ddc2 47%, #d9ccb3 100%);
  color: #2d2619;
  font-family: "Trebuchet MS", "Gill Sans", "Noto Sans", sans-serif;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.9rem 1rem;
  border-radius: 14px;
  background: rgba(255, 249, 231, 0.86);
  border: 1px solid rgba(88, 65, 34, 0.25);
}

h1 {
  margin: 0;
  font-size: 1.5rem;
}

.subtitle {
  margin: 0.15rem 0 0;
  color: #5f523f;
  font-size: 0.9rem;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.ruleset-select,
.action-button {
  border: 1px solid rgba(75, 57, 29, 0.3);
  border-radius: 8px;
  padding: 0.45rem 0.7rem;
  font: inherit;
  background: #fbf6e8;
}

.action-button {
  cursor: pointer;
  font-weight: 600;
}

.content-layout {
  min-height: 0;
  display: grid;
  grid-template-columns: 330px 1fr 340px;
  gap: 1rem;
}

.side-panel {
  min-height: 0;
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 0.9rem;
}

.board-layout {
  min-height: 0;
}

.log-panel {
  min-height: 0;
}

.status {
  margin: 0;
  padding: 1rem;
  border-radius: 10px;
  background: rgba(255, 248, 236, 0.8);
  border: 1px solid rgba(78, 58, 31, 0.2);
}

.status.error {
  color: #872c2c;
}

@media (max-width: 980px) {
  .content-layout {
    grid-template-columns: 1fr;
  }

  .side-panel {
    order: 2;
  }

  .board-layout {
    order: 1;
    min-height: 60dvh;
  }

  .log-panel {
    order: 3;
    min-height: 40dvh;
  }
}
</style>
