<script setup lang="ts">
import type {
  ActionResponsePayload,
  LegalMoveOptionPayload,
  MissilePreviewPayload,
  ShockPreviewPayload,
  UnitPayload,
} from "../../types/game";

interface Props {
  selectedUnit: UnitPayload | null;
  targetUnit: UnitPayload | null;
  movePreview: LegalMoveOptionPayload | null;
  missilePreview: MissilePreviewPayload | null;
  missilePreviewReason: string | null;
  shockPreview: ShockPreviewPayload | null;
  shockPreviewReason: string | null;
  lastActionResult: ActionResponsePayload | null;
  isSubmitting: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  "fire-missile": [];
  "resolve-shock": [];
  "reload-missile": [];
}>();
</script>

<template>
  <section class="panel">
    <header class="panel-header">
      <h2>Action Preview</h2>
      <span class="badge">Live</span>
    </header>

    <div class="block">
      <h3>Move</h3>
      <p v-if="!selectedUnit">Select a unit to inspect legal move destinations.</p>
      <p v-else-if="!movePreview">Hover a legal destination to preview route and MP cost.</p>
      <div v-else class="preview-grid">
        <p>
          <strong>Unit:</strong>
          {{ selectedUnit.unit_id }}
        </p>
        <p>
          <strong>Destination:</strong>
          ({{ movePreview.destination.q }}, {{ movePreview.destination.r }})
        </p>
        <p>
          <strong>Cost:</strong>
          {{ movePreview.total_cost }} MP
        </p>
        <p>
          <strong>Path:</strong>
          {{ movePreview.path.map((coord) => `(${coord.q},${coord.r})`).join(" -> ") }}
        </p>
      </div>
    </div>

    <div class="block">
      <h3>Combat</h3>
      <p v-if="!selectedUnit">Select a unit first.</p>
      <p v-else-if="!targetUnit">Hover enemy unit and use buttons below.</p>
      <p v-else>Target: {{ targetUnit.unit_id }} ({{ targetUnit.side }})</p>

      <div v-if="targetUnit" class="preview-grid">
        <p v-if="missilePreview">
          <strong>Missile:</strong>
          range {{ missilePreview.range_to_target }}, DR {{ missilePreview.total_drm }}, threshold
          {{ missilePreview.hit_threshold }}
        </p>
        <p v-else>
          <strong>Missile preview:</strong>
          {{ missilePreviewReason ?? "unavailable" }}
        </p>

        <p v-if="shockPreview">
          <strong>Shock:</strong>
          base {{ shockPreview.base_column }}, shift {{ shockPreview.total_shift }}, final {{ shockPreview.final_column }}
        </p>
        <p v-else>
          <strong>Shock preview:</strong>
          {{ shockPreviewReason ?? "unavailable" }}
        </p>
      </div>

      <div class="button-row">
        <button type="button" class="panel-button" :disabled="!selectedUnit || !targetUnit || isSubmitting" @click="emit('fire-missile')">
          Fire Missile
        </button>
        <button type="button" class="panel-button" :disabled="!selectedUnit || !targetUnit || isSubmitting" @click="emit('resolve-shock')">
          Resolve Shock
        </button>
        <button type="button" class="panel-button" :disabled="!selectedUnit || isSubmitting" @click="emit('reload-missile')">Reload</button>
      </div>
    </div>

    <div class="block">
      <h3>Last Result</h3>
      <p v-if="!lastActionResult">No action resolved yet.</p>
      <div v-else class="preview-grid">
        <p>
          <strong>Status:</strong>
          {{ lastActionResult.ok ? "ok" : "rejected" }}
        </p>
        <p>
          <strong>Reason:</strong>
          {{ lastActionResult.reason }}
        </p>
        <p v-if="lastActionResult.missile_outcome">
          <strong>Missile:</strong>
          {{ lastActionResult.missile_outcome.firing_unit_id }} -> {{ lastActionResult.missile_outcome.target_unit_id }} (roll
          {{ lastActionResult.missile_outcome.modified_roll }})
        </p>
        <p v-if="lastActionResult.shock_outcome">
          <strong>Shock:</strong>
          col {{ lastActionResult.shock_outcome.final_column }}, roll {{ lastActionResult.shock_outcome.roll }}
        </p>
        <p v-if="lastActionResult.morale_outcomes.length > 0">
          <strong>Morale checks:</strong>
          {{ lastActionResult.morale_outcomes.length }}
        </p>
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
h3,
p {
  margin: 0;
}

h2 {
  font-size: 1.04rem;
}

h3 {
  font-size: 0.92rem;
}

.badge {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 0.2rem 0.45rem;
  border-radius: 99px;
  background: rgba(97, 146, 113, 0.18);
  color: #3f5c42;
}

.block {
  display: grid;
  gap: 0.45rem;
  padding-top: 0.2rem;
  border-top: 1px dashed rgba(93, 71, 42, 0.24);
}

.preview-grid {
  display: grid;
  gap: 0.3rem;
  font-size: 0.9rem;
}

.button-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}

.panel-button {
  border: 1px solid rgba(78, 58, 31, 0.3);
  border-radius: 8px;
  padding: 0.45rem 0.5rem;
  font: inherit;
  cursor: pointer;
  background: #fbf6e8;
}

.panel-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

strong {
  color: #4e3f2a;
}
</style>
