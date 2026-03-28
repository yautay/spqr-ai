# Original Rules Data Import Guide

This file lists the table/scenario files prepared as templates for importing the full `original` rules data.

## Where to fill data

Rules tables:

- `apps/api/src/legions_api/data/tables/movement_costs.template.json`
- `apps/api/src/legions_api/data/tables/stacking_voluntary.template.json`
- `apps/api/src/legions_api/data/tables/stacking_mandatory.template.json`
- `apps/api/src/legions_api/data/tables/missile_range_results.template.json`
- `apps/api/src/legions_api/data/tables/shock_superiority.template.json`
- `apps/api/src/legions_api/data/tables/clash_columns.template.json`
- `apps/api/src/legions_api/data/tables/shock_crt.template.json`
- `apps/api/src/legions_api/data/tables/cohesion_tq_checks.template.json`
- `apps/api/src/legions_api/data/tables/rally_table.template.json`
- `apps/api/src/legions_api/data/tables/leader_casualty_table.template.json`
- `apps/api/src/legions_api/data/tables/pursuit_option.template.json`
- `apps/api/src/legions_api/data/tables/unit_type_traits.template.json`

Scenario templates:

- `apps/api/src/legions_api/data/scenarios/_template/map.template.json`
- `apps/api/src/legions_api/data/scenarios/_template/order_of_battle.template.json`
- `apps/api/src/legions_api/data/scenarios/_template/line_command_eligibility.template.json`
- `apps/api/src/legions_api/data/scenarios/_template/victory.template.json`
- `apps/api/src/legions_api/data/scenarios/_template/special_rules.template.json`

## Import rules

- Keep identifiers stable (`scenario_id`, `line_id`, `unit_id`, `leader_id`).
- Prefer explicit numeric values, no implicit defaults.
- If a value is not known yet, keep `null` and add a short note in `notes`.
- Do not remove keys from templates; fill them to preserve parser compatibility.

## Recommended process

1. Fill movement and combat tables first.
2. Fill one scenario end-to-end using `_template` files.
3. Run rule tests and add scenario regression tests.
4. Repeat per scenario.

## Important

Current implementation priority remains:

- full `original` parity first,
- `simple` mode later via separate table pack and rule handlers.
