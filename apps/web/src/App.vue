<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import GameBoard from "./components/map/GameBoard.vue";
import { useGameStore } from "./stores/gameStore";
import type { RulesetMode } from "./types/game";

const gameStore = useGameStore();
const selectedRuleset = ref<RulesetMode>("original");

const boardState = computed(() => gameStore.state);
const availableRulesets = computed(() => gameStore.rulesets);

onMounted(async () => {
  await gameStore.initialize();
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

async function handleNewGame(): Promise<void> {
  await gameStore.startNewGame(selectedRuleset.value);
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
        <button type="button" class="action-button" :disabled="gameStore.isSubmitting" @click="handleNewGame">
          New Game
        </button>
      </div>
    </header>

    <section class="board-layout">
      <p v-if="gameStore.isLoading" class="status">Loading game state...</p>
      <p v-else-if="gameStore.error" class="status error">{{ gameStore.error }}</p>
      <GameBoard v-else :state="boardState" />
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

.board-layout {
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
</style>
