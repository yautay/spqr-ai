<script setup lang="ts">
import type { AIMoveResponsePayload } from "../../types/game";

interface Props {
  aiMoveResponse: AIMoveResponsePayload | null;
  isSubmitting: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  "run-ai-move": [];
}>();
</script>

<template>
  <section class="panel">
    <header class="panel-header">
      <h2>AI Control</h2>
      <span class="badge">M4</span>
    </header>

    <button type="button" class="panel-button" :disabled="isSubmitting" @click="emit('run-ai-move')">Run AI Move</button>

    <p v-if="!aiMoveResponse" class="empty">Run AI move to see decision explanation.</p>

    <div v-else class="preview-grid">
      <p>
        <strong>Status:</strong>
        {{ aiMoveResponse.ok ? "ok" : "failed" }} ({{ aiMoveResponse.reason }})
      </p>
      <p>
        <strong>Considered:</strong>
        {{ aiMoveResponse.considered_actions }} actions in {{ aiMoveResponse.elapsed_ms }} ms
      </p>
      <p>
        <strong>Selected:</strong>
        {{ aiMoveResponse.selected_action?.summary ?? "none" }}
      </p>

      <div class="top-candidates">
        <strong>Top candidates</strong>
        <ol>
          <li v-for="candidate in aiMoveResponse.top_candidates" :key="`${candidate.summary}-${candidate.score}`">
            {{ candidate.summary }} ({{ candidate.score.toFixed(2) }})
          </li>
        </ol>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel {
  background: rgba(255, 248, 234, 0.9);
  border: 1px solid rgba(95, 72, 41, 0.28);
  border-radius: 14px;
  padding: 0.9rem;
  display: grid;
  gap: 0.8rem;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

h2,
p {
  margin: 0;
}

h2 {
  font-size: 1.04rem;
}

.badge {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 0.2rem 0.45rem;
  border-radius: 99px;
  background: rgba(67, 119, 153, 0.2);
  color: #2d4f68;
}

.panel-button {
  border: 1px solid rgba(78, 58, 31, 0.3);
  border-radius: 8px;
  padding: 0.45rem 0.6rem;
  font: inherit;
  cursor: pointer;
  background: #fbf6e8;
}

.panel-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.empty {
  color: #695f4f;
}

.preview-grid {
  display: grid;
  gap: 0.4rem;
  font-size: 0.9rem;
}

.top-candidates ol {
  margin: 0.35rem 0 0;
  padding-left: 1.15rem;
  display: grid;
  gap: 0.15rem;
}
</style>
