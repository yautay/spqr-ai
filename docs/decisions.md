# Decisions Log

This document records confirmed project decisions and rationale.

## D-001 Project Name

- Decision: project name is `Legions`.
- Rationale: neutral naming and product identity.

## D-002 Usage Scope

- Decision: private, non-commercial project.
- Rationale: personal play and experimentation focus.

## D-003 Technical Stack

- Decision:
  - backend/core/AI in Python,
  - frontend in Vue 3 + TypeScript,
  - battlefield renderer with PixiJS.
- Rationale: strong productivity for AI logic in Python and fast UI iteration in Vue.

## D-004 Desktop Strategy

- Decision:
  - primary desktop packaging target is Electron,
  - architecture must remain compatible with future Tauri packaging.
- Rationale: faster initial packaging path with optional later optimization.

## D-005 Architecture Rule: Engine Independence

- Decision: rules engine and AI must be independent from frontend and desktop shell.
- Rationale: testability, replay reliability, and long-term maintainability.

## D-006 Determinism Requirement

- Decision: seeded RNG and event-sourced action history are required.
- Rationale: reproducible debugging, balancing, and AI analysis.

## D-007 Local Runtime Security

- Decision: backend listens on `127.0.0.1` only in desktop mode.
- Rationale: reduce accidental exposure and simplify local trust model.

## D-008 Frontend Neutrality

- Decision: no Electron-specific APIs in web frontend.
- Rationale: preserve portability to Tauri without rewrite.

## D-009 Maintainability and Scalability Standards

- Decision: enforce clean architecture, small modules, small classes, and concise files.
- Rationale: reduce complexity growth and keep long-term maintenance cost low.

## D-010 Testing Requirement

- Decision: unit tests are mandatory for all behavior changes.
- Rationale: protect rules correctness and prevent regressions in AI/game logic.

## D-011 Static Analysis and Security Tooling

- Decision:
  - Python: `pytest`, `ruff`, `mypy`, `bandit`, `pip-audit`
  - Frontend: `vitest`, `eslint`, strict `typescript`, dependency audit in CI
- Rationale: enforce code quality, typing discipline, and vulnerability visibility from day one.

## D-012 Line Length Policy

- Decision: max line length is `140` characters.
- Rationale: allow readable signatures and structured payloads while maintaining code clarity.

## D-013 Build Orchestration

- Decision: use `just` as the canonical task runner for local development and CI entry points.
- Rationale: keep commands consistent across backend/frontend and reduce onboarding friction.

## D-014 Map Representation

- Decision: use an explicit irregular hex map model (`tiles` + optional edge metadata), not radius-only map bounds.
- Rationale: supports historical scenario shapes and avoids later migration before pathfinding and AI scaling.

## D-015 Logging

- Decision: use `loguru` for backend logging from project start.
- Rationale: simple setup, readable structured logs, and easy debug-level instrumentation during development.

## D-016 Ruleset Modes and Editable Tables

- Decision: support two selectable rulesets (`original`, `simple`) and store rule tables in editable JSON files.
- Rationale: preserve full-rules gameplay while enabling a reduced-complexity mode and easy table tuning without code edits.

## D-017 Delivery Priority for Rulesets

- Decision: implementation priority is full `original` rules first; `simple` support remains architecture-ready but deferred.
- Rationale: avoid mixing interpretations and ensure one complete, testable ruleset before adding major simplifications.

## Revisit Policy

Any decision can be revised when one of these is true:

- measurable performance issue on target hardware,
- implementation complexity exceeds acceptable cost,
- a new requirement conflicts with current decision.

When revising, append a new decision entry instead of rewriting history.
