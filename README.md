# Legions

A private, non-commercial digital tactical wargame project focused on an AI opponent that makes interesting decisions and provides a real battlefield challenge.

## Project Goal

Build a playable 1vAI experience with a faithful ancient-era tactical rules engine and an AI player capable of:
- sensible leader and unit activation,
- maintaining a coherent battle line,
- reacting to changing battlefield conditions,
- offering multiple play styles (aggressive, cautious, historical).

## Delivery Strategy

Instead of trying to build every feature immediately:
- build **rules engine + 1 battle module + 1 scenario** (vertical slice),
- reach a fully playable and correct implementation,
- then expand to additional scenarios and titles.

## Architecture (MVP)

1. **Core Rules Engine**  
   Deterministic rules engine: hexes, units, leaders, activations, ZOC, combat, morale, rout/pursuit.

2. **Game State + Event Log**  
   Every action as an event (debugging, replay, undo, AI decision analysis).

3. **Scenario Loader**  
   Scenario definitions (map, OOB, setup, victory conditions) in JSON/YAML.

4. **UI Client**  
   Hex map, modifier preview, resolution panel, and clear feedback for move legality.

5. **AI Service**  
   AI that uses the same action API as the human player.

## AI Opponent (Layered)

1. **Legal Move Generator**  
   Generates all legal moves (100% rules compliance).

2. **Evaluation Function**  
   Position scoring based on losses, morale, line cohesion, leader exposure risk, key terrain control, and momentum.

3. **Search Layer**  
   Start with beam search / MCTS under a per-decision time budget.

4. **Domain Heuristics**  
   Domain-specific rules (e.g., leader activation priorities, avoiding overextension).

5. **Style Profiles**  
   AI behavior profiles: aggressive, cautious, historical, competitive.

6. **Controlled Randomness**  
   Limited randomness to avoid repetitive play patterns.

## MVP Roadmap

1. Data model + scenario parser.  
2. Movement and zones of control (ZOC).  
3. Combat, morale, rout.  
4. Turn structure and leader activations.  
5. Playable tactical UI.  
6. AI v1 (heuristics + shallow search).  
7. Rules regression tests and AI balance tuning.  
8. Save/Load + replay + AI decision telemetry.

## Current Status

- Backend rules engine is currently through Milestone 2 (`movement + missile + shock + morale + rout/pursuit`).
- Milestone 3 playable UI slice is complete in `apps/web` (Pixi map, overlays, preview, and event log).
- Next implementation target is Milestone 4 (AI v1).

## How to Measure AI Quality

- AI win rate across selected test scenarios.
- Decision stability under turn-time constraints.
- Number of critical positional errors (e.g., exposed leaders).
- Match variety (AI does not repeat one dominant pattern).
- Clear log of "why AI chose X".

## Main Risks

- High complexity and edge cases in tactical rules interactions.
- Need for strong UI transparency (action legality, modifiers).
- Scope creep due to rules and AI complexity.

## Open Product Decisions

- Platform target: desktop or web.
- Priority: strict rules fidelity vs gameplay-first approach.
- Default AI profile: historical vs strongest possible competitor.

## Project Boundaries

- This project is intended for private use only.
- No public release is planned.
- No commercial use or monetization is planned.

## Working Docs

- `AGENT_PLAN.md` - execution rules, assumptions, and progress tracker for implementation.
- `docs/RULEBOOK_IMPLEMENTATION_PLAN.md` - consolidated rules analysis and code implementation plan.
- `docs/ORIGINAL_DATA_IMPORT_GUIDE.md` - where and how to fill original-rules tables and scenario data.
- `docs/architecture.md` - technical architecture and module boundaries.
- `docs/roadmap.md` - milestone plan with checklist status.
- `docs/decisions.md` - confirmed stack and architectural decisions.

## Development Commands

This repository uses `just` as the single task runner.

- `just bootstrap` - install backend and frontend dev dependencies
- `just lint` - run static lint checks
- `just typecheck` - run Python and TypeScript type checks
- `just test` - run backend and frontend unit tests
- `just security` - run static security and dependency audits
- `just check` - run full local quality gate
