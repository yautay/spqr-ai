<script setup lang="ts">
import { Application, Container, Graphics } from "pixi.js";
import { onMounted, onUnmounted, ref, watch } from "vue";

import { axialToPixel, buildHexPolygon, buildMapBounds, coordKey } from "./hexGeometry";
import type { GameStatePayload, HexPayload, LegalMoveOptionPayload } from "../../types/game";

interface Props {
  state: GameStatePayload | null;
  selectedUnitId?: string | null;
  hoveredUnitId?: string | null;
  hoveredHex?: HexPayload | null;
  legalMoves?: LegalMoveOptionPayload[];
}

const props = withDefaults(defineProps<Props>(), {
  selectedUnitId: null,
  hoveredUnitId: null,
  hoveredHex: null,
  legalMoves: () => [],
});

const emit = defineEmits<{
  "unit-click": [unitId: string];
  "unit-hover": [unitId: string | null];
  "hex-click": [coord: HexPayload];
  "hex-hover": [coord: HexPayload | null];
}>();

const HEX_SIZE = 36;
const BOARD_PADDING = 48;

const boardHost = ref<HTMLDivElement | null>(null);
const app = ref<Application | null>(null);

onMounted(() => {
  void mountBoard();
});

onUnmounted(() => {
  const activeApp = app.value;
  if (!activeApp) {
    return;
  }

  activeApp.destroy(true, { children: true });
  app.value = null;
});

watch(
  () => [props.state, props.selectedUnitId, props.hoveredUnitId, props.hoveredHex, props.legalMoves],
  () => {
    renderBoard();
  },
  { deep: true }
);

async function mountBoard(): Promise<void> {
  if (!boardHost.value) {
    return;
  }

  const pixi = new Application();
  await pixi.init({
    resizeTo: boardHost.value,
    antialias: true,
    autoDensity: true,
    backgroundAlpha: 0,
  });

  boardHost.value.appendChild(pixi.canvas);
  app.value = pixi;
  renderBoard();
}

function renderBoard(): void {
  if (!props.state || !app.value) {
    return;
  }

  const stage = app.value.stage;
  stage.removeChildren().forEach((child) => {
    child.destroy({ children: true });
  });

  const root = new Container();
  const mapLayer = new Container();
  const overlayLayer = new Container();
  const unitLayer = new Container();

  const bounds = buildMapBounds(
    props.state.tiles.map((tile) => tile.coord),
    HEX_SIZE
  );
  const boardWidth = bounds.maxX - bounds.minX;
  const boardHeight = bounds.maxY - bounds.minY;
  const scaleX = (app.value.screen.width - BOARD_PADDING * 2) / boardWidth;
  const scaleY = (app.value.screen.height - BOARD_PADDING * 2) / boardHeight;
  const boardScale = Math.max(0.55, Math.min(1.6, Math.min(scaleX, scaleY)));

  root.scale.set(boardScale);
  root.position.set(
    app.value.screen.width / 2 - ((bounds.minX + bounds.maxX) * boardScale) / 2,
    app.value.screen.height / 2 - ((bounds.minY + bounds.maxY) * boardScale) / 2
  );

  const legalMoveByHex = new Map(props.legalMoves.map((option) => [coordKey(option.destination), option]));
  const hoveredHexKey = props.hoveredHex ? coordKey(props.hoveredHex) : null;

  for (const tile of props.state.tiles) {
    const center = axialToPixel(tile.coord, HEX_SIZE);
    const points = buildHexPolygon(center, HEX_SIZE - 1.5);
    const tileGraphic = new Graphics();

    tileGraphic.lineStyle(1.5, 0x243343, 0.9);
    tileGraphic.beginFill(terrainColor(tile.terrain));
    tileGraphic.drawPolygon(points);
    tileGraphic.endFill();
    tileGraphic.eventMode = "static";
    tileGraphic.cursor = "pointer";
    tileGraphic.on("pointertap", () => emit("hex-click", tile.coord));
    tileGraphic.on("pointerover", () => emit("hex-hover", tile.coord));
    tileGraphic.on("pointerout", () => emit("hex-hover", null));
    mapLayer.addChild(tileGraphic);

    const tileKey = coordKey(tile.coord);
    const isHovered = tileKey === hoveredHexKey;
    const isLegalDestination = legalMoveByHex.has(tileKey);
    if (!isHovered && !isLegalDestination) {
      continue;
    }

    const overlay = new Graphics();
    const overlayColor = isHovered ? 0xf2e394 : 0x6bcf93;
    const overlayAlpha = isHovered ? 0.27 : 0.18;
    overlay.beginFill(overlayColor, overlayAlpha);
    overlay.drawPolygon(points);
    overlay.endFill();
    overlayLayer.addChild(overlay);
  }

  const unitsByHex = new Map<string, typeof props.state.units>();
  for (const unit of props.state.units) {
    const key = coordKey(unit.position);
    const grouped = unitsByHex.get(key) ?? [];
    grouped.push(unit);
    unitsByHex.set(key, grouped);
  }

  for (const [hexKey, units] of unitsByHex.entries()) {
    const [q, r] = hexKey.split(",").map((value) => Number(value));
    const center = axialToPixel({ q, r }, HEX_SIZE);
    const stackCount = units.length;

    units.forEach((unit, index) => {
      const slotOffset = stackCount === 1 ? 0 : (index - (stackCount - 1) / 2) * 12;
      const radius = 10;
      const unitGraphic = new Graphics();
      const isSelected = unit.unit_id === props.selectedUnitId;
      const isHovered = unit.unit_id === props.hoveredUnitId;

      unitGraphic.lineStyle(isSelected ? 3 : isHovered ? 2.5 : 1.25, isSelected ? 0xf6d66f : 0x1f2933);
      unitGraphic.beginFill(unit.side === "red" ? 0xbf4040 : 0x3c6fb8, unit.is_routed ? 0.45 : 0.95);
      unitGraphic.drawCircle(center.x + slotOffset, center.y, radius);
      unitGraphic.endFill();

      unitGraphic.eventMode = "static";
      unitGraphic.cursor = "pointer";
      unitGraphic.on("pointertap", () => emit("unit-click", unit.unit_id));
      unitGraphic.on("pointerover", () => emit("unit-hover", unit.unit_id));
      unitGraphic.on("pointerout", () => emit("unit-hover", null));
      unitLayer.addChild(unitGraphic);
    });
  }

  root.addChild(mapLayer);
  root.addChild(overlayLayer);
  root.addChild(unitLayer);
  stage.addChild(root);
}

function terrainColor(terrain: string): number {
  switch (terrain) {
    case "clear":
      return 0xcfbe8a;
    case "rough":
      return 0xb29875;
    case "woods":
      return 0x5f7757;
    case "road":
      return 0xc9b3a2;
    case "water":
      return 0x5a87b4;
    default:
      return 0x9ca3af;
  }
}
</script>

<template>
  <div ref="boardHost" class="board-host" />
</template>

<style scoped>
.board-host {
  width: 100%;
  height: 100%;
  min-height: 420px;
  border: 1px solid rgba(79, 70, 48, 0.4);
  border-radius: 16px;
  background:
    radial-gradient(circle at 12% 20%, rgba(248, 228, 187, 0.44), transparent 36%),
    radial-gradient(circle at 85% 78%, rgba(104, 129, 162, 0.33), transparent 42%),
    linear-gradient(165deg, #f2e7ca 0%, #e4d7b8 100%);
  overflow: hidden;
}
</style>
