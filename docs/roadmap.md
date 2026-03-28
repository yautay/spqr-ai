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

- [~] Define game state models (hex, unit, leader, turn)
- [x] Implement coordinate and hex utility module
- [x] Implement movement rules
- [x] Implement zones of control (ZOC)
- [x] Implement action validation entry point

## Milestone 2 - Combat and Morale

- [ ] Implement combat resolution pipeline
- [ ] Implement combat modifiers
- [ ] Implement morale checks
- [ ] Implement rout and pursuit behavior
- [ ] Add regression tests for combat edge cases

## Milestone 3 - Playable UI Slice

- [ ] Render hex map via PixiJS
- [ ] Add hover, selection, and unit details panel
- [ ] Add legal move overlay
- [ ] Add action preview and modifier panel
- [ ] Add event log panel

## Milestone 4 - AI v1

- [ ] Integrate legal move generator
- [ ] Implement heuristic position evaluator
- [ ] Add shallow search with move time budget
- [ ] Add AI decision explanation metadata
- [ ] Run AI-vs-AI smoke simulations

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

- [ ] Unit and integration tests pass
- [ ] Deterministic replay still valid
- [ ] API/schema updates documented
- [ ] No shell-specific code leaked into `apps/web`
