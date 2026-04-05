<script setup lang="ts">
import { computed } from "vue";

import type { Side, UnitPayload } from "@shared-schema/game";

interface Props {
  selectedUnit: UnitPayload | null;
  hoveredUnit: UnitPayload | null;
  activeSide: Side | null;
}

const props = defineProps<Props>();

const displayUnit = computed(() => props.selectedUnit ?? props.hoveredUnit);
const displayLabel = computed(() => {
  if (props.selectedUnit) {
    return "Selected unit";
  }

  if (props.hoveredUnit) {
    return "Hovered unit";
  }

  return "No unit selected";
});
</script>

<template>
  <section class="panel">
    <header class="panel-header">
      <h2>Unit Details</h2>
      <span class="badge">{{ displayLabel }}</span>
    </header>

    <p v-if="!displayUnit" class="empty">Click or hover a unit on the map to inspect its state.</p>

    <dl v-else class="stats-grid">
      <div>
        <dt>Unit ID</dt>
        <dd>{{ displayUnit.unit_id }}</dd>
      </div>
      <div>
        <dt>Side</dt>
        <dd>{{ displayUnit.side }}</dd>
      </div>
      <div>
        <dt>Position</dt>
        <dd>{{ displayUnit.position.q }}, {{ displayUnit.position.r }}</dd>
      </div>
      <div>
        <dt>Move</dt>
        <dd>{{ displayUnit.move_allowance }}</dd>
      </div>
      <div>
        <dt>TQ</dt>
        <dd>{{ displayUnit.tq }}</dd>
      </div>
      <div>
        <dt>Cohesion</dt>
        <dd>{{ displayUnit.cohesion_hits }}</dd>
      </div>
      <div>
        <dt>Routed</dt>
        <dd>{{ displayUnit.is_routed ? "yes" : "no" }}</dd>
      </div>
      <div>
        <dt>ZOC</dt>
        <dd>{{ displayUnit.exerts_zoc ? "yes" : "no" }}</dd>
      </div>
      <div>
        <dt>Missile Class</dt>
        <dd>{{ displayUnit.missile_class_id ?? "-" }}</dd>
      </div>
      <div>
        <dt>Missile Supply</dt>
        <dd>{{ displayUnit.missile_supply }}</dd>
      </div>
      <div>
        <dt>Shock Type</dt>
        <dd>{{ displayUnit.shock_type }}</dd>
      </div>
      <div>
        <dt>Pursuit</dt>
        <dd>{{ displayUnit.pursuit_capable ? "yes" : "no" }}</dd>
      </div>
      <div>
        <dt>Active Side</dt>
        <dd>{{ activeSide ?? "-" }}</dd>
      </div>
    </dl>
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
  gap: 0.5rem;
}

h2 {
  margin: 0;
  font-size: 1.04rem;
}

.badge {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 0.2rem 0.45rem;
  border-radius: 99px;
  background: rgba(155, 136, 95, 0.2);
  color: #5e4f35;
}

.empty {
  margin: 0;
  color: #695f4f;
}

.stats-grid {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem 0.8rem;
}

dt {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: #6b604b;
}

dd {
  margin: 0.15rem 0 0;
  font-weight: 600;
}
</style>
