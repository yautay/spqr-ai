import { ref } from "vue";
import { defineStore } from "pinia";

import { normalizeActionResult, type ActionKind } from "../domain/logs/normalizeActionResult";
import type { LogDraftEntry, LogEntry, LogLevel } from "../domain/logs/types";
import type { ActionResponsePayload, GameEventPayload } from "@shared-schema/game";

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
  const seenEventIds = ref<Set<string>>(new Set());

  function append(level: LogLevel, title: string, detail: string): void {
    appendMany([{ level, title, detail }]);
  }

  function appendMany(drafts: LogDraftEntry[]): void {
    entries.value = [...drafts.map((draft) => buildLogEntry(draft.level, draft.title, draft.detail)), ...entries.value];
  }

  function appendActionResult(actionKind: ActionKind, result: ActionResponsePayload): void {
    appendMany(normalizeActionResult(actionKind, result));
  }

  function appendGameEvent(event: GameEventPayload): void {
    if (seenEventIds.value.has(event.event_id)) {
      return;
    }

    seenEventIds.value.add(event.event_id);
    append(resolveEventLevel(event), resolveEventTitle(event), resolveEventDetail(event));
  }

  function clear(): void {
    entries.value = [];
    seenEventIds.value = new Set();
  }

  return {
    entries,
    append,
    appendMany,
    appendActionResult,
    appendGameEvent,
    clear,
  };
});

function resolveEventLevel(event: GameEventPayload): LogLevel {
  if (event.ok === false) {
    return "warning";
  }

  if (event.event_type === "ai_move_selected") {
    return "success";
  }

  return "info";
}

function resolveEventTitle(event: GameEventPayload): string {
  switch (event.event_type) {
    case "game_reset":
      return "Game reset";
    case "activation_advanced":
      return "Activation advanced";
    case "turn_ended":
      return "Turn ended";
    case "move_resolved":
      return "Move resolved";
    case "missile_resolved":
      return "Missile resolved";
    case "reload_resolved":
      return "Reload resolved";
    case "shock_resolved":
      return "Shock resolved";
    case "ai_thinking":
      return "AI thinking";
    case "ai_move_selected":
      return "AI move selected";
  }
}

function resolveEventDetail(event: GameEventPayload): string {
  const detailParts = Object.entries(event.details).map(([key, value]) => `${key}=${String(value)}`);
  const details = detailParts.length > 0 ? detailParts.join(", ") : "no details";
  const reason = event.reason ?? "no reason";
  return `${reason}; ${details}`;
}
