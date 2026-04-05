# Architecture

## Overview

Legions is split into independent layers so the game can run as web app first and later as desktop app under Electron or Tauri.

Core design goal: game rules and AI remain engine-agnostic and UI-agnostic.

## System Layers

### 1) Rules and AI backend (`apps/api`)

Responsibilities:

- game state model
- action validation and resolution
- turn and activation flow
- combat, morale, rout/pursuit
- AI decision making
- save/load and replay support

Implementation target:

- Python 3.x
- FastAPI for command/query endpoints
- WebSocket stream for live game events

### 2) Web frontend (`apps/web`)

Responsibilities:

- map visualization and unit interaction
- legal move highlights and previews
- combat/modifier display
- event log and turn controls
- AI action playback feedback

Implementation target:

- Vue 3 + TypeScript
- PixiJS for hex map rendering

### 3) Shared contracts (`packages/shared-schema`)

Responsibilities:

- request/response schemas
- event payload schemas
- generated frontend types from backend source of truth

## Domain Boundaries

The backend separates pure domain code from transport and persistence concerns.

Suggested structure:

```text
apps/api/src/
  core/
    model/
    rules/
    actions/
    events/
    turn/
    rng/
  ai/
    eval/
    search/
    profiles/
  api/
    routes/
    ws/
  persistence/
  tests/
```

Rules for boundaries:

- `core/` must not depend on FastAPI.
- `core/` must not depend on desktop packaging details.
- AI uses the same legal action interface as human player actions.

## Map Data Model (Axial + Irregular)

The map model is designed for pathfinding and scenario flexibility from day one.

- Coordinates: axial hex (`q`, `r`) with derived `s = -q - r`
- Static map graph:
  - `tiles: dict[HexCoord, HexTile]`
  - `edges: dict[EdgeKey, MapEdge]` for blocked links and movement modifiers
- Dynamic state:
  - `units_by_id`
  - `occupant_by_hex` index for O(1) occupancy checks

Runtime geometry notes:

- unit facing is modeled as a hex-vertex angle: `0/60/120/180/240/300`
- single-hex units expose `2` front, `2` flank, and `2` rear adjacent hexes
- wide units use a two-hex footprint (`position` + optional `position_b`)
- occupancy indexes all occupied hexes of the footprint, not only the anchor hex
- ZOC and shock adjacency/angle must be derived from shared geometry helpers, not ad hoc per-rule math
- wide-unit movement is being implemented incrementally; occupancy and combat geometry are footprint-aware, but advanced phalanx pivots/wheeling remain a separate rules milestone

This allows A* pathfinding, movement cost evaluation, and future terrain/edge effects without redesign.

## Ruleset and Tables

- Runtime supports two ruleset profiles: `original` and `simple`.
- Ruleset profile is selected when creating a new game and stored in game state.
- Tables are externalized as editable JSON files in `apps/api/src/legions_api/data/rulesets/`.
- Current table-driven fields include terrain movement costs and ZOC movement lock behavior.

## Action Pipeline

All move execution follows one deterministic flow:

1. Receive command
2. Validate legal action against current state
3. Resolve state transitions
4. Emit ordered events
5. Persist event log entry

This guarantees replay, debugging, and AI parity.

## Runtime Interfaces

### REST

- `POST /game/new`
- `GET /game/scenarios`
- `GET /game/state`
- `POST /game/activation/advance`
- `POST /game/action`
- `POST /game/end-turn`
- `POST /ai/move`
- `POST /game/save`
- `POST /game/load`
- `GET /game/saves`
- `GET /game/replay`
- `GET /game/replay/verify`

### WebSocket

Example events:

- `game_reset`
- `activation_advanced`
- `move_resolved`
- `shock_resolved`
- `morale_resolved`
- `rout_resolved`
- `turn_ended`
- `ai_thinking`
- `ai_move_selected`

## Determinism and Replay

Determinism requirements:

- seeded RNG for all random outcomes
- stable event order
- replay from events reconstructs equivalent state

Replay support is required for debugging and AI quality analysis.

## Desktop Compatibility Constraints

To stay compatible with both Electron and Tauri:

- frontend must use HTTP/WebSocket to a local backend only
- avoid direct shell APIs in the frontend
- isolate shell integrations in dedicated desktop adapters
- backend listens on `127.0.0.1` only in desktop mode

## Performance Baseline (Low-Spec Friendly)

- cap render framerate when needed
- avoid expensive post-processing effects
- keep AI decision budget bounded per move
- make visual effects configurable by profile (`low-spec`, `normal`)
