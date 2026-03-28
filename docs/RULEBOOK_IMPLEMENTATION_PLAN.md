# Legions Rules Implementation Plan (From Reference Rulebook)

This document captures the analysis and implementation strategy derived from:

- `docs/SPQR_4thEdition_Living_Rules_Draft_Oct2022.pdf`

Purpose:

- avoid re-reading/re-analyzing the full rulebook in future sessions,
- define a stable coding plan for `original` and `simple` rulesets,
- keep rules implementation table-driven and maintainable.

## 1) Scope and Coding Targets

Current coding target is tactical engine parity for core battle loop:

1. Sequence of Play
2. Leader activation / orders / momentum / trump
3. Movement + facing + ZOC + withdrawals
4. Missile combat
5. Shock combat
6. Special units (elephants, phalanx, manipular behavior, artillery)
7. Cohesion/rout/rally/depletion/engaged
8. Army withdrawal and victory

`simple` mode should be implemented as profile overrides on top of the same engine, not a separate engine.

## 2) Engine Architecture (Canonical)

Use strict layers:

- `core/model`: immutable state, enums, value objects
- `core/tables`: JSON-driven rules tables + loaders + validators
- `core/rules`: pure functions for validation/resolution
- `core/turn`: sequence orchestration and phase transitions
- `core/events`: typed domain events for replay/debug
- `api/*`: transport only (FastAPI, schemas, routes)

Hard rule: all outcomes are produced by `validate -> resolve -> emit events`.

## 3) Domain Modules and Responsibilities

### 3.1 Sequence/Turn Engine

Implement explicit phase state machine:

- Leader Activation Phase
- Orders Phase
  - Movement and Missile segment
  - Shock segment
- Momentum/Return to activation
- Rout and Reload Phase
- Withdrawal Phase

Must support:

- leader states (`inactive`, `active`, `finished`, `trumped/bypassed`),
- turn-level reset of temporary markers,
- deterministic order of resolution.

### 3.2 Leader and Command Module

Implement:

- initiative order activation (lowest first, tie handling),
- individual orders by initiative value,
- line commands with eligibility constraints,
- OC exceptions (move out of ZOC, move leaders, regroup cavalry, etc.),
- momentum and die-roll-of-doom branch,
- trump options (active trump, trump-the-trump, momentum trump),
- elite commander initiative phase,
- leader casualty checks and replacement logic.

### 3.3 Movement/Facing/ZOC Module

Implement:

- movement costs + cohesion from terrain/elevation,
- one move per unit per Orders Phase,
- repeat-move-in-turn cohesion penalty,
- facing rules (including reaction facing change),
- ZOC entry/exit restrictions,
- special movement:
  - phalanx maneuvers,
  - column movement,
  - orderly withdrawal,
  - pre-arranged withdrawal.

Pathfinding note:

- movement legality should use graph search with rule-aware policy,
- but many moves are local and should have fast-path checks before full A*.

### 3.4 Missile Module

Implement:

- active missile fire and movement/fire interaction,
- LOS rules and blockers,
- reaction fire (entry/retire/return),
- missile supply (`low/no`) transitions,
- reload rules,
- H&D tactics,
- leader casualty from missile.

### 3.5 Shock Module

Implement exact resolution order:

1. shock designation
2. pre-shock TQ checks (charge)
3. leader casualty check
4. clash column determination
5. superiority and size ratio adjustments
6. CRT resolution
7. collapse/rout checks
8. advance after combat
9. cavalry pursuit

Must preserve simultaneous-step semantics where specified.

### 3.6 Special Units Module

Implement unit-specific rules:

- war elephants:
  - pass-thru,
  - screens,
  - rampage,
  - cavalry interactions,
  - Indian vs African modifiers,
- skirmisher/velites/light-infantry special behavior,
- phalanx defense and double-depth,
- manipular line extension,
- triarii doctrine gate,
- scorpio artillery modes and fire cadence.

### 3.7 Cohesion/Rout/Rally Module

Implement:

- cohesion hit accumulation,
- TQ checks,
- rout movement priorities and blocking logic,
- rout-through-stacking penalties,
- rally attempts and outcomes,
- depletion state and effects,
- optional engaged rule.

### 3.8 Victory Module

Implement:

- rout point accounting,
- withdrawal threshold checks,
- tie resolution logic.

## 4) Table-Driven Data Plan

All values likely to vary by scenario/ruleset should live in JSON, not code.

Recommended data files:

- `data/rulesets/original.json`
- `data/rulesets/simple.json`
- `data/tables/movement_costs.json`
- `data/tables/zoc_rules.json`
- `data/tables/missile_table.json`
- `data/tables/shock_superiority.json`
- `data/tables/clash_columns.json`
- `data/tables/shock_crt.json`
- `data/tables/rally_table.json`
- `data/tables/pursuit_table.json`
- `data/tables/unit_type_traits.json`

Scenario-specific files:

- `data/scenarios/<scenario_id>/map.json`
- `data/scenarios/<scenario_id>/order_of_battle.json`
- `data/scenarios/<scenario_id>/line_command_eligibility.json`
- `data/scenarios/<scenario_id>/victory.json`
- `data/scenarios/<scenario_id>/special_rules.json`

## 4.1 Missing Data Checklist (Original Rules)

Below is the concrete list of data still needed to finish `original` parity cleanly.

Core tables still missing in repo:

- full Movement Cost Chart (by unit type/class, terrain, elevation, facing)
- Stacking Charts (voluntary and mandatory)
- Missile Range and Results Chart
- Shock Superiority Chart
- Clash of Spears and Swords Chart
- Shock Combat Results Table (CRT)
- Cohesion Hit and TQ Check Chart (machine-readable triggers)
- Rally Table
- Leader Casualty Table
- Cavalry Pursuit option table values (if optional used)

Scenario-bound data still missing:

- line command eligibility charts per scenario
- retreat edges per side
- army withdrawal levels and RP scoring metadata
- reinforcement timing and entry conditions
- scenario-specific restrictions/exceptions (especially special units)

When you provide any of the above, prefer JSON/CSV with stable IDs.

## 5) Original vs Simple Ruleset Strategy

Implement `simple` as explicit override toggles and table substitutions.

Already confirmed:

- `zoc_locks_movement`: `true` in `original`, `false` in `simple`.

Planned additional simplification toggles:

- reduced leader command friction (fewer failed command rolls),
- reduced or disabled advanced optional subsystems (e.g. engaged),
- simplified missile depletion behavior,
- simplified cavalry pursuit behavior,
- reduced special-case penalties where appropriate.

Rule profile object should be the single source for feature toggles:

- `RulesetDefinition.options.*`

## 5.1 Architecture Guardrails for Future Simple Mode

From public descriptions of Simple GBoH (online product/rules summaries), the simplified mode appears to reduce complexity in:

- leader activation/command friction,
- shock and missile resolution overhead,
- orderly withdrawal and elephant complexity,
- rout/stacking detail and edge-case handling.

Because Simple may diverge significantly, design now for pluggable rules behavior:

- keep phase orchestration fixed, but make rule handlers swappable per profile,
- encapsulate each major subsystem behind strategy interfaces:
  - `CommandRules`, `MovementRules`, `MissileRules`, `ShockRules`, `RoutRules`, `SpecialUnitRules`,
- allow table packs per ruleset (`original` pack, future `simple` pack),
- avoid hardcoding assumptions that every subsystem is active.

Implementation hint:

- create a `RulesetRuntime` object composed from profile handlers and table references,
- pass `RulesetRuntime` into all resolution entrypoints.

## 6) Phased Implementation Roadmap

### Phase A (Current foundation - in progress)

- irregular axial map model
- movement + ZOC baseline
- A* pathfinding policy layer
- base game endpoints and ruleset selection

### Phase B (Leader/Turn Core)

- full activation sequencing
- momentum + trump + elite initiative
- order accounting + per-phase move/fire limits

### Phase C (Missile + Shock Core)

- complete missile flow (LOS/reactions/supply/reload)
- complete shock pipeline with table-driven CRT
- advance and pursuit

### Phase D (Special Units and Edge Rules)

- elephants, phalanx advanced maneuvers, manipular extensions, artillery
- triarii doctrine and scenario-conditioned behavior

### Phase E (Rout/Rally/Victory)

- full rout pathing and stacking penalties
- rally/depletion
- army withdrawal victory loop

### Phase F (AI Integration)

- legal action generator over full ruleset
- evaluation using rules-aware state features
- explainable move selection with debug logs

## 7) Test Strategy (Must-Have)

### Unit tests

- coordinate math and adjacency
- map graph and blocked-edge handling
- ZOC and facing primitives
- table loader validation and schema guardrails

### Rule tests

- one focused test per non-trivial rule paragraph
- edge cases for phalanx movement and double-depth
- missile LOS + reaction-fire timing
- shock simultaneous-step correctness
- rout path priority and forced elimination

### Scenario regression tests

- deterministic scripted turn snippets from known setups
- compare resulting state and event stream snapshots

### Invariants/property tests

- no illegal occupancy,
- no impossible facing states,
- deterministic replay with same seed + command stream.

## 8) Logging and Debug Plan

Use `loguru` with structured context fields:

- `turn`, `phase`, `active_leader`, `action_id`, `ruleset`, `scenario_id`, `unit_ids`

Emit domain-level debug events for:

- command validation failures,
- ZOC lock reasons,
- pathfinding decision summary,
- shock calculation breakdown (base column, shifts, superiority, final hits),
- rout/rally transition reasons.

Keep logs explainable for AI and rules debugging.

## 9) Open Inputs Still Needed from Scenario Book

To complete parity, we still need scenario-book data extraction for:

- per-scenario setup,
- line command eligibility charts,
- retreat edges,
- army withdrawal levels,
- scenario-specific exceptions/optional notes.

## 10) Session Handoff Checklist

Any new coding session should do this first:

1. Read this file.
2. Read `docs/decisions.md` and `AGENT_PLAN.md`.
3. Confirm current milestone in `docs/roadmap.md`.
4. Implement smallest vertical slice with tests.
5. Update roadmap checkboxes and decisions if any rule interpretation changed.

## 11) Implementation Priority Order (Recommended Next)

1. Leader activation + momentum/trump engine
2. Full Shock pipeline with table-driven CRT
3. Missile reaction and supply/reload completion
4. Rout/rally/depletion completion
5. Elephants and phalanx advanced modules
6. Scenario loader + line command eligibility integration

This order gives fastest path to a fully playable loop and unlocks AI training/simulation quality early.
