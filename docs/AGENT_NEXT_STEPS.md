# Agent Next Steps

This file captures the current engineering handoff state after the 2026-04-05 session.

## Current Code State

- branch: `master`
- latest commits:
  - `c1efc29 Stabilize wide unit movement validation`
  - `f6fedb4 Add basic movement for wide phalanx units`
  - `78c28c8 Add footprint-aware geometry for wide units`
  - `1fd989a Align facing and shock geometry with vertex arcs`
- backend tests: passing (`144 passed`)
- web tests: passing
- web typecheck: passing

## What Is Done

- leaders and leader-driven activation baseline
- scenario metadata loading baseline
- vertex-angle facing model (`0/60/120/180/240/300`)
- front-only ZOC baseline
- shock angle derived from board geometry
- wide-unit footprint model via `position` + optional `position_b`
- footprint-aware occupancy index
- footprint-aware ZOC and shock adjacency/angle
- basic wide-unit movement:
  - straight-ahead translation
  - reverse-face validation path

## What Is Explicitly Not Done Yet

- front-to-flank maneuver
- wheeling maneuver
- exact reverse-face restrictions and costs from rulebook
- column movement
- orderly withdrawal
- pre-arranged withdrawal
- reaction facing changes
- repeat-move penalties
- wide-unit missile/LOS handling
- full shock depth (pre-shock, leader casualties, size-ratio, full advance-after-combat details)
- special units package
- rout/rally/depletion/withdrawal/victory closure

## Recommended Next Implementation Order

1. Finish `Movement/Facing/ZOC` parity:
   - front-to-flank maneuver
   - wheeling maneuver
   - reverse-face restrictions/costs
   - column rules
   - orderly withdrawal / pre-arranged withdrawal
2. Expand `Shock` parity:
   - pre-shock checks
   - leader interactions/casualties
   - size ratio
   - advance after combat for wide units
3. Expand `Missile` parity:
   - wide-unit LOS/range semantics
   - H&D
4. Implement `Special Units`:
   - elephants
   - phalanx defense / double-depth
   - manipular extension
   - triarii doctrine
   - artillery
5. Close `Rout/Rally/Withdrawal/Victory`

## Rules/Design Constraints To Preserve

- do not revert to named directional facings like `NE/E/...` for unit orientation
- keep vertex-angle facing as the source of truth
- keep geometry shared across movement, ZOC, missile, and shock
- prefer explicit `not implemented` rejection over fake one-hex behavior for wide-unit rules not yet modeled
- keep transport contracts thin; rules truth must remain in `core/*`

## Testing Expectations For Next Session

- every new paragraph-sized rule should get at least one focused test
- prefer scenario-like fixtures for phalanx maneuvers
- after changes run:
  - `pytest apps/api/tests -q`
  - `npm run typecheck` in `apps/web`
  - `npm run test:run` in `apps/web`
