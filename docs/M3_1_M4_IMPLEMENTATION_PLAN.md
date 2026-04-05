# M3.1 + M4 Implementation Plan

Status: completed.

## Scope

- Close Milestone 3.1 (UI hardening + live events + preview before execute).
- Close Milestone 4 (AI legal action generation, evaluation, bounded search, explainability, smoke sims).

## Delivery Phases

1. M3.1 backend preview APIs (`/game/preview/missile`, `/game/preview/shock`) and contracts.
2. M3.1 backend WebSocket stream (`/game/ws/events`) with emitted events after state-changing commands.
3. M3.1 frontend WebSocket subscription and action preview wiring.
4. M4 backend legal action generator and deterministic scoring model.
5. M4 backend bounded shallow search + `/ai/move` endpoint with explainability payload.
6. M4 smoke simulation utility (AI-vs-AI) and regression tests.
7. Final quality pass (`just check`) and roadmap updates.

## Definition of Done

### Milestone 3.1

- Frontend receives live action events from WebSocket and appends them to event log.
- Missile and shock previews are available before command execution.
- Preview endpoints are read-only and do not mutate state or RNG counter.
- API and frontend tests cover preview/event contracts.

### Milestone 4

- AI can enumerate legal actions for active side using same rule pipeline as human commands.
- AI evaluator returns deterministic position score.
- AI search honors move-time budget and returns explainability metadata.
- `/ai/move` executes selected action and returns both action result and decision context.
- AI-vs-AI smoke simulation runs under tests and remains deterministic with fixed seed.
