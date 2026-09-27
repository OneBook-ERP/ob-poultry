# Fit-Gap Analysis — Poultry Module

Maps every requirement in [BRD.md](./BRD.md) against what exists today in `ob_poultry`'s Poultry module (doctypes under `ob_poultry/ob_poultry/poultry/doctype/`). **Fit** = requirement is met as built. **Partial** = a doctype/field exists but the business rule isn't fully implemented. **Gap** = nothing exists yet.

*Updated 2026-09-28 — the original version of this file only reflected the as-built v1 core; Epics 1–9 (v1.1 gap closure), the v2 contract-farming/hatchery slice, and 13 Query Reports have since shipped. All of that is now marked Fit below. The one new section (Daily Register Parity) reflects real gaps surfaced from a customer's actual paper register.*

## Flock & batch management

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-FLK-01 | Sheds with capacity | **Fit** | `Poultry Shed` — `shed_name`, `capacity`, `location`, `is_active` |
| BR-FLK-02 | Breed master with type + standard FCR | **Fit** | `Poultry Breed` — `breed_type`, `standard_fcr` |
| BR-FLK-03 | Batch placement, capacity check | **Fit** | `Poultry Batch.validate_shed_capacity()` |
| BR-FLK-04 | Derived current bird count | **Fit** | `Poultry Batch.recalculate_performance()` sums submitted `Poultry Daily Log` rows |
| BR-FLK-05 | Mortality/cull cap at initial count | **Fit** | `Poultry Daily Log.validate_bird_count()` |
| BR-FLK-06 | Cause- and sex-coded mortality | **Fit** | `Poultry Daily Log Mortality Entry` child table (`cause`, `sex`, `count`, `description`, `photo`); `mortality_count` is a computed rollup |
| BR-FLK-07 | Feed consumption depletes stock | **Fit** | `Poultry Daily Log.create_feed_stock_entry()` |
| BR-FLK-08 | Daily body weight + water | **Fit** | Recorded; body weight now feeds FCR/CFCR and the Bodyweight Report |
| BR-FLK-09 | FCR / CFCR per batch | **Fit** | `Poultry Batch.recalculate_performance()` computes both from cumulative feed and latest body weight |
| BR-FLK-10 | Standard benchmarks vs. actual | **Fit** | `Poultry Benchmark` (breed + age-keyed); `Poultry Daily Log.apply_benchmarks()` looks up the nearest earlier age |
| BR-FLK-11 | Batch closure | **Fit** | `Poultry Batch.close_batch()` **and** `Poultry Daily Log.validate_batch_not_closed()` blocks new logs against a closed batch (closed in Epic 9 — the original version of this file flagged this as the one open item) |
| BR-FLK-12 | Per-day mortality/loss % | **Fit** | `Poultry Daily Log.compute_daily_mortality_pct()` — `daily_mortality_pct` field, safe-at-zero guard |

## Egg production

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-EGG-01 | Graded egg ledger with opening/closing/avg weight | **Fit** | `Poultry Daily Log Egg Entry` — grade, opening/production/closing count, avg weight |
| BR-EGG-02 | HDEP % computation | **Fit** | `Poultry Daily Log.compute_egg_rollup()` |
| BR-EGG-03 | Tray count per grade | **Fit** | `Poultry Daily Log Egg Entry.trays`, computed from `Poultry Settings.eggs_per_tray` (Single doctype, default 30) in `compute_egg_rollup()` |

**Note on BR-EGG-01:** grade options now include Double Yolk and Dirty Egg (the latter surfaced from the customer's "Data Entry" field list, distinct from Damage) alongside Hatching / Table / Jumbo / Cracked / Waste.

## Vaccination

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-VAC-01 | Breed vaccination schedule template | **Fit** | `Poultry Vaccination Schedule Template` + `Poultry Vaccination Schedule Item` |
| BR-VAC-02 | Per-batch due-list generated at placement | **Fit** | `Poultry Batch.after_insert()` &rarr; `create_vaccination_due_rows()` &rarr; `Poultry Vaccination Due` |
| BR-VAC-03 | Record administration with validation | **Fit** | `Poultry Vaccination Record`, optionally linked to a `Poultry Vaccination Due` row to close it out |

## Feed manufacturing

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-FED-01 | Formula with ingredients + computed % | **Fit** | `Poultry Feed Formula` + `Poultry Feed Formula Ingredient` |
| BR-FED-02 | Raw material vs. medicine distinction | **Fit** | `Poultry Feed Formula Ingredient.category`; `raw_material_total_kg`/`medicine_total_kg` rollups |
| BR-FED-03 | Generate BOM, produce via Work Order at a multiple | **Fit** | `Poultry Feed Formula.create_or_update_bom()`, `Poultry Feed Production.create_work_order()`, both with Desk UI buttons |
| BR-FED-04 | Actual output + yield % | **Fit** | `Poultry Feed Production.actual_output_kg` &rarr; `yield_percent` |
| BR-FED-05 | Cost per kg surfaced | **Partial** | `Poultry Feed Production.cost_per_kg` exists but is intentionally left unset (FRD §2.7) — not yet wired to actual Work Order costing |
| BR-FED-06 | Feed logged in an alternate unit (bags), converted to stock UOM | **Fit** | `Poultry Daily Log.feed_uom`/`feed_qty`, converted via ERPNext's `get_conversion_factor()` in `apply_feed_uom_conversion()`; blank `feed_uom` keeps the original direct-kg-entry behavior |
| BR-FED-07 | Feed cost/valuation per batch and date | **Fit** | Poultry Feed Consumption Report now joins `Stock Entry Detail` on `stock_entry` for `feed_cost`/`cumulative_feed_cost` |
| BR-FED-08 | Production cost per egg | **Fit** | New **Poultry Egg Production Cost** report: feed cost &divide; eggs produced, per batch/date range |

## Expenses

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-EXP-01 | Ad hoc daily expenses per batch | **Fit** | New child doctype `Poultry Daily Log Expense` (description, amount); `Poultry Daily Log.expenses` + `total_expenses` rollup |

## Egg sales

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-SALES-01 | Egg sale against a customer, itemized by grade/qty/rate | **Fit** | New submittable doctype `Poultry Egg Sale` + `Poultry Egg Sale Item`, reuses ERPNext's `Customer` |
| BR-SALES-02 | Sale reduces the egg stock ledger | **Fit** | `Poultry Egg Sale.validate_against_stock()` caps against production minus prior sales; new **Poultry Net Egg Stock** report nets production vs. sales per batch/grade at report time (production ledger itself stays immutable, per FRD §3.7's design note) |

## System

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-SYS-01 | Built on ERPNext's own Item/BOM/Work Order/Stock Entry | **Fit** | No parallel inventory or manufacturing model exists anywhere in the module |
| BR-SYS-02 | Role-scoped permissions | **Fit** | `Poultry Manager`, `Poultry Attendant`, `Vaccination In-charge`, `Feed Mill Operator` — all four roles exist with scoped permissions across all 21 doctypes |
| BR-SYS-03 | Shed carries a default feed warehouse | **Fit** | `Poultry Shed.default_feed_warehouse`; `Poultry Batch.default_feed_warehouse_from_shed()` fills a blank `feed_warehouse` on a new batch without overriding an explicit choice |

## Summary

| Status | Count |
|---|---|
| Fit | 32 |
| Partial | 1 |
| Gap | 0 |

*Updated again 2026-09-28 — Daily Register Parity (Epics 11-19) shipped and verified (21/21 integration tests, plus a direct report-output check for the three report-only items). Every BR is now Fit except one deliberately-deferred item (feed cost/kg, BR-FED-05, tracked in ROADMAP.md's v2-depth list).* Design is in [FRD.md](./FRD.md) §3; execution breakdown is in [TASKS_AND_TEST_CASES.md](./TASKS_AND_TEST_CASES.md) Epics 11-19.
