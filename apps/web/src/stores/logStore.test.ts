import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useLogStore } from "./logStore";

describe("logStore websocket dedup", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("does not append duplicate websocket events", () => {
    const store = useLogStore();

    const event = {
      event_id: "evt-1",
      timestamp: new Date().toISOString(),
      event_type: "move_resolved" as const,
      ok: true,
      reason: "ok",
      details: { unit_id: "r1" },
    };

    store.appendGameEvent(event);
    store.appendGameEvent(event);

    expect(store.entries).toHaveLength(1);
    expect(store.entries[0].title).toBe("Move resolved");
  });
});
