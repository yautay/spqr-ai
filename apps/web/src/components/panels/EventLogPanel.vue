<script setup lang="ts">
import type { LogEntry } from "../../domain/logs/types";

interface Props {
  entries: LogEntry[];
}

defineProps<Props>();
</script>

<template>
  <section class="panel">
    <header class="panel-header">
      <h2>Event Log</h2>
      <span class="count">{{ entries.length }}</span>
    </header>

    <p v-if="entries.length === 0" class="empty">No events yet. Resolve an action to populate the log.</p>

    <ul v-else class="entries">
      <li v-for="entry in entries" :key="entry.id" class="entry">
        <div class="entry-top">
          <strong :class="`level-${entry.level}`">{{ entry.title }}</strong>
          <time>{{ new Date(entry.timestamp).toLocaleTimeString() }}</time>
        </div>
        <p>{{ entry.detail }}</p>
      </li>
    </ul>
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
  min-height: 0;
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

.count {
  padding: 0.15rem 0.45rem;
  border-radius: 99px;
  background: rgba(138, 113, 72, 0.16);
  font-weight: 600;
  font-size: 0.8rem;
}

.empty {
  color: #695f4f;
}

.entries {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.6rem;
  overflow: auto;
}

.entry {
  border: 1px solid rgba(93, 71, 42, 0.17);
  background: rgba(255, 253, 246, 0.72);
  border-radius: 10px;
  padding: 0.55rem;
  display: grid;
  gap: 0.3rem;
}

.entry-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
}

strong {
  font-size: 0.9rem;
}

time {
  font-size: 0.74rem;
  color: #6b5c44;
}

.level-info {
  color: #29445f;
}

.level-success {
  color: #2c5f39;
}

.level-warning {
  color: #7a4e17;
}

.level-error {
  color: #8a2b2b;
}
</style>
