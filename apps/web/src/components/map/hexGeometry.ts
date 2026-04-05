import type { HexPayload } from "../../types/game";

const SQRT_3 = Math.sqrt(3);

export interface PixelPoint {
  x: number;
  y: number;
}

export interface PixelBounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

export function coordKey(coord: HexPayload): string {
  return `${coord.q},${coord.r}`;
}

export function axialToPixel(coord: HexPayload, hexSize: number): PixelPoint {
  return {
    x: hexSize * SQRT_3 * (coord.q + coord.r / 2),
    y: hexSize * 1.5 * coord.r,
  };
}

export function buildHexPolygon(center: PixelPoint, hexSize: number): number[] {
  const points: number[] = [];

  for (let corner = 0; corner < 6; corner += 1) {
    const angle = (Math.PI / 180) * (60 * corner - 30);
    points.push(center.x + hexSize * Math.cos(angle));
    points.push(center.y + hexSize * Math.sin(angle));
  }

  return points;
}

export function buildMapBounds(coords: HexPayload[], hexSize: number): PixelBounds {
  if (coords.length === 0) {
    return {
      minX: -hexSize,
      minY: -hexSize,
      maxX: hexSize,
      maxY: hexSize,
    };
  }

  const pixels = coords.map((coord) => axialToPixel(coord, hexSize));
  const xs = pixels.map((point) => point.x);
  const ys = pixels.map((point) => point.y);

  return {
    minX: Math.min(...xs) - hexSize,
    minY: Math.min(...ys) - hexSize,
    maxX: Math.max(...xs) + hexSize,
    maxY: Math.max(...ys) + hexSize,
  };
}
