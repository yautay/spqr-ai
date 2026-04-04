"""Map models and helper builders for irregular hex scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from legions_api.core.model.hex import HexCoord


class TerrainType(StrEnum):
    """Terrain classes used by movement and future combat modifiers."""

    CLEAR = "clear"
    ROUGH = "rough"
    WOODS = "woods"
    ROAD = "road"
    WATER = "water"


@dataclass(frozen=True, slots=True)
class HexTile:
    """Static tile data for one map hex."""

    coord: HexCoord
    terrain: TerrainType = TerrainType.CLEAR
    move_cost: int = 1
    passable: bool = True
    elevation_level: int = 0
    blocks_line_of_sight: bool = False


@dataclass(frozen=True, slots=True)
class MapEdge:
    """Bidirectional edge metadata between adjacent hexes."""

    blocks_movement: bool = False
    movement_cost_delta: int = 0
    blocks_line_of_sight: bool = False


EdgeKey = tuple[HexCoord, HexCoord]


def edge_key(a: HexCoord, b: HexCoord) -> EdgeKey:
    """Return canonical key for an undirected edge."""

    if (a.q, a.r) <= (b.q, b.r):
        return (a, b)
    return (b, a)


@dataclass(frozen=True, slots=True)
class ScenarioMap:
    """Static map graph for movement and pathfinding."""

    tiles: dict[HexCoord, HexTile]
    edges: dict[EdgeKey, MapEdge]

    def contains(self, coord: HexCoord) -> bool:
        """Return True when coordinate exists on map and is passable."""

        tile = self.tiles.get(coord)
        return tile is not None and tile.passable

    def tile_at(self, coord: HexCoord) -> HexTile | None:
        """Return tile for provided coordinate."""

        return self.tiles.get(coord)

    def neighbors(self, coord: HexCoord) -> tuple[HexCoord, ...]:
        """Return passable neighboring coordinates reachable by adjacency."""

        neighbors: list[HexCoord] = []
        for candidate in coord.neighbors():
            if not self.contains(candidate):
                continue

            edge = self.edges.get(edge_key(coord, candidate))
            if edge is not None and edge.blocks_movement:
                continue

            neighbors.append(candidate)

        return tuple(neighbors)

    def movement_cost(self, origin: HexCoord, destination: HexCoord) -> int:
        """Return movement cost from origin to destination over an adjacent edge."""

        tile = self.tiles.get(destination)
        if tile is None:
            raise ValueError("destination is outside scenario map")

        edge = self.edges.get(edge_key(origin, destination))
        edge_delta = edge.movement_cost_delta if edge is not None else 0
        return max(1, tile.move_cost + edge_delta)


def build_irregular_map(tiles: list[HexTile], edges: dict[EdgeKey, MapEdge] | None = None) -> ScenarioMap:
    """Create a scenario map from explicit tile list and optional edge metadata."""

    tile_lookup = {tile.coord: tile for tile in tiles}
    return ScenarioMap(tiles=tile_lookup, edges=edges or {})
