import { describe, expect, it } from "vitest";

import { normalizeActionResult } from "./normalizeActionResult";
import type { ActionResponsePayload, GameStatePayload } from "@shared-schema/game";

const EMPTY_STATE: GameStatePayload = {
  ruleset: "original",
  turn_phase: "orders",
  tiles: [],
  active_side: "red",
  units: [],
};

describe("normalizeActionResult", () => {
  it("creates summary and outcome entries for move actions", () => {
    const result: ActionResponsePayload = {
      ok: true,
      reason: "ok",
      state: EMPTY_STATE,
      effects: [],
      pending_tq_checks: [],
      tq_check_outcomes: [
        {
          unit_id: "b1",
          location: { q: 1, r: 0 },
          source: "stacking",
          required: true,
          formula: "tq-1",
          drm: 0,
          target: 6,
          roll: 7,
          passed: false,
          applied_cohesion_hits: 1,
          became_routed: true,
        },
      ],
      missile_outcome: null,
      shock_outcome: null,
      morale_outcomes: [],
      pursuit_outcome: null,
      events: [],
    };

    const entries = normalizeActionResult("move", result);

    expect(entries[0].title).toBe("Move resolved");
    expect(entries.some((entry) => entry.title === "TQ check failed")).toBe(true);
  });

  it("includes missile event details", () => {
    const result: ActionResponsePayload = {
      ok: true,
      reason: "ok",
      state: EMPTY_STATE,
      effects: [],
      pending_tq_checks: [],
      tq_check_outcomes: [],
      missile_outcome: {
        firing_unit_id: "r1",
        target_unit_id: "b1",
        fire_mode: "active",
        reaction_trigger: null,
        missile_class_id: "A",
        range_to_target: 2,
        table_strength: 7,
        base_roll: 6,
        total_drm: 1,
        modified_roll: 7,
        hit: true,
        applied_cohesion_hits: 1,
        drm_breakdown: [],
      },
      shock_outcome: null,
      morale_outcomes: [],
      pursuit_outcome: null,
      events: [
        {
          event_type: "missile_fired",
          unit_id: "r1",
          target_unit_id: "b1",
          reaction_trigger: null,
          roll: 6,
          target: null,
          success: true,
          supply_before: null,
          supply_after: null,
        },
      ],
    };

    const entries = normalizeActionResult("missile", result);

    expect(entries.some((entry) => entry.title === "Missile hit")).toBe(true);
    expect(entries.some((entry) => entry.title === "Missile fired")).toBe(true);
  });
});
