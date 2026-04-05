import { describe, expect, it } from "vitest";

import { axialToPixel, buildHexPolygon, buildMapBounds, coordKey } from "./hexGeometry";

describe("hexGeometry", () => {
  it("builds stable coordinate keys", () => {
    expect(coordKey({ q: 2, r: -1 })).toBe("2,-1");
  });

  it("maps axial coordinates to pointy-top pixel space", () => {
    const point = axialToPixel({ q: 1, r: -1 }, 10);

    expect(point.x).toBeCloseTo(8.66, 2);
    expect(point.y).toBe(-15);
  });

  it("returns six-corner polygon vertex list", () => {
    const polygon = buildHexPolygon({ x: 0, y: 0 }, 20);

    expect(polygon).toHaveLength(12);
  });

  it("computes map bounds with default margin", () => {
    const bounds = buildMapBounds(
      [
        { q: 0, r: 0 },
        { q: 1, r: 0 },
        { q: 0, r: 1 },
      ],
      10,
    );

    expect(bounds.maxX).toBeGreaterThan(bounds.minX);
    expect(bounds.maxY).toBeGreaterThan(bounds.minY);
  });
});
