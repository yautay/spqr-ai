"""A* pathfinding for hex maps with occupancy and ZOC-aware policies."""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush

from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.unit import Side
from legions_api.core.rules.zoc import enemy_zoc_hexes


@dataclass(frozen=True, slots=True)
class MovementPolicy:
    """Runtime movement constraints used by pathfinding."""

    max_cost: int
    ignore_occupied: bool = False
    allow_enter_enemy_zoc: bool = True
    stop_on_enter_enemy_zoc: bool = False


@dataclass(frozen=True, slots=True)
class PathResult:
    """Computed path plus diagnostics for debugging and UI explanation."""

    found: bool
    path: tuple[HexCoord, ...]
    total_cost: int
    visited_nodes: int
    reason: str


def shortest_path(state: GameState, side: Side, start: HexCoord, goal: HexCoord, policy: MovementPolicy) -> PathResult:
    """Run A* over scenario graph while honoring occupancy and optional ZOC constraints."""

    if not state.scenario_map.contains(goal):
        return PathResult(found=False, path=(), total_cost=0, visited_nodes=0, reason="goal_out_of_map")

    if start == goal:
        return PathResult(found=True, path=(start,), total_cost=0, visited_nodes=0, reason="ok")

    enemy_zoc = enemy_zoc_hexes(state, side)
    frontier: list[tuple[int, int, int, HexCoord]] = []
    push_index = 0
    heappush(frontier, (start.distance_to(goal), 0, push_index, start))
    came_from: dict[HexCoord, HexCoord | None] = {start: None}
    cost_so_far: dict[HexCoord, int] = {start: 0}
    visited_nodes = 0

    while frontier:
        _, current_cost, _, current = heappop(frontier)
        visited_nodes += 1

        if current == goal:
            path = _rebuild_path(came_from, current)
            return PathResult(found=True, path=path, total_cost=current_cost, visited_nodes=visited_nodes, reason="ok")

        if policy.stop_on_enter_enemy_zoc and current in enemy_zoc and current != start:
            continue

        for neighbor in state.scenario_map.neighbors(current):
            if not policy.ignore_occupied and neighbor != goal and neighbor in state.occupant_by_hex:
                continue
            if not policy.allow_enter_enemy_zoc and neighbor in enemy_zoc:
                continue

            step_cost = state.scenario_map.movement_cost(current, neighbor)
            new_cost = current_cost + step_cost
            if new_cost > policy.max_cost:
                continue

            best_known = cost_so_far.get(neighbor)
            if best_known is not None and new_cost >= best_known:
                continue

            cost_so_far[neighbor] = new_cost
            came_from[neighbor] = current
            priority = new_cost + neighbor.distance_to(goal)
            push_index += 1
            heappush(frontier, (priority, new_cost, push_index, neighbor))

    return PathResult(found=False, path=(), total_cost=0, visited_nodes=visited_nodes, reason="no_path")


def _rebuild_path(came_from: dict[HexCoord, HexCoord | None], current: HexCoord) -> tuple[HexCoord, ...]:
    """Build ordered path from A* predecessor dictionary."""

    path: list[HexCoord] = [current]
    while True:
        predecessor = came_from[current]
        if predecessor is None:
            break
        path.append(predecessor)
        current = predecessor

    path.reverse()
    return tuple(path)
