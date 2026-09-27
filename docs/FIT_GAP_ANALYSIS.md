# Fit-Gap Analysis — Poultry Module

Maps every requirement in [BRD.md](./BRD.md) against what exists today in `ob_poultry`'s Poultry module (doctypes under `ob_poultry/ob_poultry/poultry/doctype/`). **Fit** = requirement is met as built. **Partial** = a doctype/field exists but the business rule isn't fully implemented. **Gap** = nothing exists yet.

## Flock & batch management

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-FLK-01 | Sheds with capacity | **Fit** | `Poultry Shed` — `shed_name`, `capacity`, `location`, `is_active` |
| BR-FLK-02 | Breed master with type + standard FCR | **Fit** | `Poultry Breed` — `breed_type` (Broiler/Layer/Breeder/Dual Purpose), `standard_fcr`. `standard_fcr` is stored but not yet consumed by any calculation (see BR-FLK-09) |
| BR-FLK-03 | Batch placement, capacity check | **Fit** | `Poultry Batch.validate_shed_capacity()` rejects `initial_bird_count > shed.capacity` |
| BR-FLK-04 | Derived current bird count | **Fit** | `Poultry Batch.recalculate_bird_count()` sums submitted `Poultry Daily Log` mortality/cull rows; never hand-edited |
| BR-FLK-05 | Mortality/cull cap at initial count | **Fit** | `Poultry Daily Log.validate_bird_count()` sums existing submitted rows + this row and rejects if it exceeds `initial_bird_count` |
| BR-FLK-06 | Cause- and sex-coded mortality | **Gap** | `Poultry Daily Log` has flat `mortality_count` / `cull_count` integers only — no cause, no sex split |
| BR-FLK-07 | Feed consumption depletes stock | **Fit** | `Poultry Daily Log.create_feed_stock_entry()` posts a Stock Entry (Material Issue) against `Poultry Batch.feed_warehouse` on submit, reverses on cancel |
| BR-FLK-08 | Daily body weight + water | **Fit** | `Poultry Daily Log.average_body_weight_g`, `water_consumed_liters` — recorded but not yet aggregated into any batch-level metric |
| BR-FLK-09 | FCR / CFCR per batch | **Gap** | No cumulative feed or cumulative weight-gain calculation exists anywhere; `standard_fcr` on `Poultry Breed` is unused |
| BR-FLK-10 | Standard benchmarks vs. actual | **Gap** | No benchmark doctype; no age-keyed standard curve for mortality %, feed/bird, or body weight |
| BR-FLK-11 | Batch closure | **Fit** | `Poultry Batch.close_batch()` — sets status Closed + end date; no doctype-level block on new `Poultry Daily Log` rows against a closed batch yet (see Gap note below) |

**Note on BR-FLK-11:** `close_batch()` exists but `Poultry Daily Log.validate()` does not currently check `batch.status == "Closed"` before allowing a new submission — a closed batch can still silently receive new daily logs. Flagged as a **Partial**, not a clean Fit, and carried into the FRD as a required fix.

## Egg production

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-EGG-01 | Graded egg ledger with opening/closing/avg weight | **Gap** | `Poultry Daily Log.egg_count` is a single flat integer — no grade, no opening/closing reconciliation, no average weight |
| BR-EGG-02 | HDEP % computation | **Gap** | Not computed; depends on BR-EGG-01 existing first |

## Vaccination

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-VAC-01 | Breed vaccination schedule template | **Gap** | No template doctype; nothing keyed by bird age |
| BR-VAC-02 | Per-batch due-list generated at placement | **Gap** | Depends on BR-VAC-01 |
| BR-VAC-03 | Record administration with validation | **Fit** | `Poultry Vaccination Record` — `vaccine_name`, `dose`, `date_given`, `next_due_date`, `administered_by`; `validate()` rejects `next_due_date <= date_given`. Currently free-standing (ad hoc), not linked to a due-list item |

## Feed manufacturing

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-FED-01 | Formula with ingredients + computed % | **Fit** | `Poultry Feed Formula` + `Poultry Feed Formula Ingredient`; `calculate_percentages()` computes `percentage` per ingredient in `validate()` |
| BR-FED-02 | Raw material vs. medicine distinction | **Gap** | `Poultry Feed Formula Ingredient` has no category field — flat ingredient list |
| BR-FED-03 | Generate BOM, produce via Work Order at a multiple | **Fit** | `Poultry Feed Formula.create_or_update_bom()` and `.make_work_order(planned_qty)` — verified end-to-end against a seeded ERPNext Company/Item Group/UOM in a rolled-back test |
| BR-FED-04 | Actual output + yield % | **Gap** | No field or report compares actual Work Order output to `batch_size_kg &times; multiple` |
| BR-FED-05 | Cost per kg surfaced | **Gap** | ERPNext's BOM/Work Order compute this internally, but nothing in the Poultry module surfaces it to a Feed Mill Operator without leaving the module |

## System

| BR | Requirement | Status | Detail |
|---|---|---|---|
| BR-SYS-01 | Built on ERPNext's own Item/BOM/Work Order/Stock Entry | **Fit** | No parallel inventory or manufacturing model was created; every doctype above links to standard ERPNext Item/Warehouse/BOM/Work Order/Stock Entry |
| BR-SYS-02 | Role-scoped permissions | **Gap** | Every doctype currently grants full CRUD (and submit/cancel where applicable) to `System Manager` only — no `Poultry Manager`, `Poultry Attendant`, or `Vaccination In-charge` role exists |

## Summary

| Status | Count |
|---|---|
| Fit | 9 |
| Partial | 1 |
| Gap | 10 |

The as-built module fully covers batch lifecycle bookkeeping (bird counts, feed stock depletion, formula-to-BOM-to-Work-Order) — the mechanically hardest, highest-risk-of-drift part of the system. What's missing is entirely on the **performance-measurement and scheduling** side: cause-coded mortality, graded eggs, FCR/CFCR, standard benchmarks, and vaccination scheduling. None of the gaps require re-architecting what exists; all extend it. Detailed closure design is in [FRD.md](./FRD.md); execution breakdown is in [TASKS_AND_TEST_CASES.md](./TASKS_AND_TEST_CASES.md).
