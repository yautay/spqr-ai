import { ref } from "vue";
import { defineStore } from "pinia";

import { normalizeActionResult, type ActionKind } from "../domain/logs/normalizeActionResult";
import type { LogDraftEntry, LogEntry, LogLevel } from "../domain/logs/types";
import type { ActionResponsePayload } from "../types/game";

function buildLogEntry(level: LogLevel, title: string, detail: string): LogEntry {
  return {
    id: buildEntryId(),
    timestamp: new Date().toISOString(),
    level,
    title,
    detail,
  };
}

function buildEntryId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }

  return `${Date.now()}-${Math.round(Math.random() * 1_000_000)}`;
}

export const useLogStore = defineStore("log", () => {
  const entries = ref<LogEntry[]>([]);

  function append(level: LogLevel, title: string, detail: string): void {
    appendMany([{ level, title, detail }]);
  }

  function appendMany(drafts: LogDraftEntry[]): void {
    entries.value = [...drafts.map((draft) => buildLogEntry(draft.level, draft.title, draft.detail)), ...entries.value];
  }

  function appendActionResult(actionKind: ActionKind, result: ActionResponsePayload): void {
    appendMany(normalizeActionResult(actionKind, result));
  }

  function clear(): void {
    entries.value = [];
  }

  return {
    entries,
    append,
    appendMany,
    appendActionResult,
    clear,
  };
});
