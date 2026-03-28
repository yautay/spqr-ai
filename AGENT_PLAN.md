# Legions Agent Plan

This file is the operational source of truth for coding agents working in this repository.
It defines assumptions, architecture guardrails, and a progress checklist.

## Project Intent

- Name: `Legions`
- Usage: private, non-commercial
- Product shape: single-player tactical wargame with AI opponent
- Rendering: 2D hex battlefield

## Confirmed Stack

- Backend and game core: `Python`
- Frontend: `Vue 3 + TypeScript`
- Battlefield renderer: `PixiJS`
- Desktop packaging path:
  - primary target: `Electron`
  - codebase requirement: compatible with future `Tauri` packaging
- Build orchestration: `just` (single entry point for local and CI tasks)

## Ruleset Delivery Priority

- Implement and validate `original` rules first.
- Keep architecture compatible with future `simple` ruleset replacement/overrides.
- Do not dilute original parity to fit a guessed simple interpretation.

## Non-Negotiable Technical Rules

- Keep game logic independent from UI and desktop shell.
- Use one action pipeline for player and AI: `validate -> resolve -> emit events`.
- Keep simulations deterministic using seeded RNG and event replay.
- Backend must bind to `127.0.0.1` only in desktop mode.
- Frontend must not depend on Electron-specific APIs.
- Use adapter boundaries for filesystem paths and process lifecycle.

## Engineering Standards (Must Follow)

- Prioritize maintainability, scalability, and performance in every change.
- Keep modules small and focused; avoid large classes and "god objects".
- Keep files compact; split code before files become hard to navigate.
- Use clear naming and explicit interfaces between modules.
- Document non-obvious behavior with concise docstrings and module docs.
- Add/update tests with every behavior change; unit tests are mandatory.
- Keep architecture layered and dependency direction clean.

## Code Style and Size Constraints

- Maximum line length: `140` characters.
- Prefer small functions with single responsibility.
- Avoid deeply nested conditionals; refactor into helpers.
- Avoid duplicated logic; extract reusable components/utilities.

## Required Quality and Security Tooling

Add and maintain the following tooling from project start.

### Python (`apps/api`)

- `pytest` for unit tests
- `ruff` for linting and formatting
- `mypy` for static type checking
- `bandit` for static security analysis
- `pip-audit` for dependency vulnerability scanning

### Frontend (`apps/web`)

- `vitest` for unit tests
- `eslint` for static linting
- `typescript` strict mode for type safety
- `npm audit` (or `pnpm audit`) in CI for dependency checks

### CI Quality Gates

Every PR/build should run and pass:

- tests
- linters
- type checks
- security scans

## Repository Target Layout

```text
apps/
  api/
  web/
  desktop-electron/
  desktop-tauri/
packages/
  shared-schema/
docs/
```

## Execution Workflow for Agents

1. Read `docs/RULEBOOK_IMPLEMENTATION_PLAN.md` before implementation.
2. Read `docs/decisions.md` before implementation.
3. Update `docs/roadmap.md` task statuses during work.
4. Implement features in smallest testable slices.
5. Add tests for rules behavior and deterministic replay.
6. Run quality gates via `just check` before completion.
7. Record any architectural change in `docs/decisions.md`.

## Status Legend

- `[ ]` not started
- `[~]` in progress
- `[x]` done
- `[!]` blocked

## Master Progress Checklist

### Foundation

- [x] Initialize `apps/api` (FastAPI skeleton)
- [x] Initialize `apps/web` (Vue + TS skeleton)
- [ ] Add shared schema package and API contracts
- [x] Add `Justfile` and standard task recipes
- [x] Add lint, formatting, and test scripts

### Rules Core

- [x] Implement map coordinates and hex utilities
- [x] Implement movement and ZOC rules
- [x] Implement action validation and resolution pipeline
- [ ] Implement turn structure and activation flow

### Combat Loop

- [ ] Implement combat resolution and modifiers
- [ ] Implement morale checks
- [ ] Implement rout and pursuit
- [ ] Emit events for each combat step

### Frontend Playability

- [ ] Render hex map with PixiJS
- [ ] Implement selection and legal-move overlays
- [ ] Build action preview and event log panels
- [ ] Hook REST commands and websocket event stream

### AI v1

- [ ] Build legal move generator integration
- [ ] Add heuristic evaluation function
- [ ] Add shallow search with time budget
- [ ] Add explainability field for selected moves

### Persistence and Replay

- [ ] Save/load game state
- [ ] Event log replay
- [ ] Deterministic replay verification tests

### Desktop Packaging

- [ ] Add Electron shell and local backend process runner
- [ ] Add packaging pipeline for desktop build
- [ ] Validate frontend remains Tauri-compatible
- [ ] Prototype Tauri shell with same frontend/backend contract

## Definition of Done

A task is done only when:

- behavior is covered by tests where relevant,
- API/event contracts are documented,
- deterministic replay remains stable,
- no shell-specific coupling leaks into core or web app.
