# Roadmap

Status legend:

- `[ ]` not started
- `[~]` in progress
- `[x]` done
- `[!]` blocked

## Milestone 0 - Foundation

- [x] Create backend skeleton (`apps/api`)
- [x] Create frontend skeleton (`apps/web`)
- [ ] Add shared schema package (`packages/shared-schema`)
- [x] Add project scripts (lint, test, typecheck, security)
- [x] Configure Python tooling: `pytest`, `ruff`, `mypy`, `bandit`, `pip-audit`
- [x] Configure frontend tooling: `vitest`, `eslint`, strict `typescript`
- [x] Set max line length to `140` for configured linters/formatters
- [ ] Add CI baseline checks (tests, lint, typecheck, security scans)

## Milestone 1 - Core Movement Loop

- [x] Define game state models (hex, unit baseline, deterministic RNG state)
- [x] Implement coordinate and hex utility module
- [x] Implement movement rules
- [x] Implement zones of control (ZOC)
- [x] Implement action validation entry point
- [x] Implement stacking side effects and TQ checks from table lookups

## Milestone 1.5 - Missile Baseline

- [x] Implement table-driven missile range resolution
- [x] Implement missile DR modifier lookup and outcome breakdown
- [x] Implement missile supply transitions (`normal -> low -> no`) and reload attempts
- [x] Implement LOS validation and movement-linked reaction windows

## Milestone 2 - Combat and Morale

- [x] Implement combat resolution pipeline
- [x] Implement combat modifiers
- [x] Implement morale checks
- [x] Implement rout and pursuit behavior
- [x] Add regression tests for combat edge cases

## Milestone 3 - Playable UI Slice

- [x] Render hex map via PixiJS
- [x] Add hover, selection, and unit details panel
- [x] Add legal move overlay
- [x] Add action preview and modifier panel
- [x] Add event log panel

## Milestone 3.1 - UI Hardening and Live Events

- [x] Add backend read-only preview endpoints for missile and shock actions
- [x] Add backend WebSocket event stream for live action events
- [x] Subscribe frontend event log to WebSocket stream with reconnect handling
- [x] Render pre-execution missile and shock preview in action panel
- [x] Add regression tests for preview/websocket payload contracts

## Milestone 4 - AI v1

- [x] Integrate legal move generator
- [x] Implement heuristic position evaluator
- [x] Add shallow search with move time budget
- [x] Add AI decision explanation metadata
- [x] Run AI-vs-AI smoke simulations

## Milestone 5 - Save/Load and Replay

- [ ] Persist game state snapshots
- [ ] Persist event logs
- [ ] Implement replay from event history
- [ ] Add deterministic replay tests with fixed seeds

## Milestone 6 - Desktop Packaging

- [ ] Add Electron shell app
- [ ] Start/stop local backend process from shell
- [ ] Package desktop build (first target platform)
- [ ] Validate frontend neutrality for Tauri migration
- [ ] Prototype Tauri shell compatibility

## Quality Gates

Before marking a milestone complete:

- [x] Unit and integration tests pass
- [x] Deterministic replay still valid
- [x] API/schema updates documented
- [x] No shell-specific code leaked into `apps/web`
