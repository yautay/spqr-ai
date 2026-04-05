import { ref } from "vue";
import { defineStore } from "pinia";

import type { LogEntry, LogLevel } from "../domain/logs/types";

function buildLogEntry(level: LogLevel, title: string, detail: string): LogEntry {
  return {
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    level,
    title,
    detail,
  };
}

export const useLogStore = defineStore("log", () => {
  const entries = ref<LogEntry[]>([]);

  function append(level: LogLevel, title: string, detail: string): void {
    entries.value = [buildLogEntry(level, title, detail), ...entries.value];
  }

  function clear(): void {
    entries.value = [];
  }

  return {
    entries,
    append,
    clear,
  };
});
