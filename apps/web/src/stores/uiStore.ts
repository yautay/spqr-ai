import { ref } from "vue";
import { defineStore } from "pinia";

import type { HexPayload } from "../types/game";

export const useUiStore = defineStore("ui", () => {
  const selectedUnitId = ref<string | null>(null);
  const hoveredUnitId = ref<string | null>(null);
  const hoveredHex = ref<HexPayload | null>(null);
  const selectedDestination = ref<HexPayload | null>(null);

  function setSelectedUnit(unitId: string | null): void {
    selectedUnitId.value = unitId;
    if (!unitId) {
      selectedDestination.value = null;
    }
  }

  function setHoveredUnit(unitId: string | null): void {
    hoveredUnitId.value = unitId;
  }

  function setHoveredHex(coord: HexPayload | null): void {
    hoveredHex.value = coord;
  }

  function setSelectedDestination(coord: HexPayload | null): void {
    selectedDestination.value = coord;
  }

  function resetSelections(): void {
    selectedUnitId.value = null;
    hoveredUnitId.value = null;
    hoveredHex.value = null;
    selectedDestination.value = null;
  }

  return {
    selectedUnitId,
    hoveredUnitId,
    hoveredHex,
    selectedDestination,
    setSelectedUnit,
    setHoveredUnit,
    setHoveredHex,
    setSelectedDestination,
    resetSelections,
  };
});
