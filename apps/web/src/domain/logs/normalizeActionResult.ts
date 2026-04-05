import type { ActionResponsePayload, MissileEventPayload } from "@shared-schema/game";
import type { LogDraftEntry } from "./types";

export type ActionKind = "move" | "missile" | "shock" | "reload";

export function normalizeActionResult(actionKind: ActionKind, result: ActionResponsePayload): LogDraftEntry[] {
  const entries: LogDraftEntry[] = [];
  const summaryLevel: LogDraftEntry["level"] = result.ok ? "success" : "warning";

  entries.push({
    level: summaryLevel,
    title: `${capitalize(actionKind)} ${result.ok ? "resolved" : "rejected"}`,
    detail: result.reason,
  });

  entries.push(
    ...result.tq_check_outcomes.map(
      (outcome): LogDraftEntry => ({
        level: outcome.passed ? "info" : "warning",
        title: `TQ check ${outcome.passed ? "passed" : "failed"}`,
        detail: `${outcome.unit_id} roll ${outcome.roll} vs ${outcome.target} (${outcome.source})`,
      }),
    ),
  );

  if (result.missile_outcome) {
    entries.push({
      level: result.missile_outcome.hit ? "success" : "info",
      title: `Missile ${result.missile_outcome.hit ? "hit" : "miss"}`,
      detail: `${result.missile_outcome.firing_unit_id} -> ${result.missile_outcome.target_unit_id} at range ${result.missile_outcome.range_to_target}`,
    });
  }

  if (result.shock_outcome) {
    entries.push({
      level: "info",
      title: "Shock resolved",
      detail: `${result.shock_outcome.attacker_unit_id} vs ${result.shock_outcome.defender_unit_id} | col ${result.shock_outcome.final_column}`,
    });
  }

  entries.push(
    ...result.morale_outcomes.map(
      (outcome): LogDraftEntry => ({
        level: outcome.passed ? "info" : "warning",
        title: `Morale ${outcome.passed ? "passed" : "failed"}`,
        detail: `${outcome.unit_id} roll ${outcome.roll} vs ${outcome.target}`,
      }),
    ),
  );

  if (result.pursuit_outcome) {
    entries.push({
      level: "info",
      title: "Pursuit move",
      detail: `${result.pursuit_outcome.unit_id} -> (${result.pursuit_outcome.destination.q}, ${result.pursuit_outcome.destination.r})`,
    });
  }

  entries.push(...result.events.map(normalizeMissileEvent));

  return entries;
}

function normalizeMissileEvent(event: MissileEventPayload): LogDraftEntry {
  switch (event.event_type) {
    case "missile_fired":
      return {
        level: "info",
        title: "Missile fired",
        detail: `${event.unit_id} fired at ${event.target_unit_id ?? "?"}`,
      };
    case "reaction_fire":
      return {
        level: "info",
        title: "Reaction fire",
        detail: `${event.unit_id} used ${event.reaction_trigger ?? "unknown"} trigger`,
      };
    case "reload_attempt":
      return {
        level: event.success ? "success" : "warning",
        title: "Reload attempt",
        detail: `${event.unit_id} ${event.success ? "reloaded" : "failed reload"}`,
      };
    case "supply_changed":
      return {
        level: "info",
        title: "Missile supply",
        detail: `${event.unit_id}: ${event.supply_before ?? "?"} -> ${event.supply_after ?? "?"}`,
      };
    case "reaction_window_opened":
      return {
        level: "info",
        title: "Reaction window opened",
        detail: `${event.unit_id} can react vs ${event.target_unit_id ?? "?"} (${event.reaction_trigger ?? "?"})`,
      };
    case "reaction_window_spent":
      return {
        level: "info",
        title: "Reaction window spent",
        detail: `${event.unit_id} spent ${event.reaction_trigger ?? "?"} reaction`,
      };
  }
}

function capitalize(value: string): string {
  if (!value) {
    return value;
  }

  return `${value[0].toUpperCase()}${value.slice(1)}`;
}
