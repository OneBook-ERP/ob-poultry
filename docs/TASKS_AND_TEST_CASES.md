# Tasks & Test Cases — Poultry Module

**Status: implemented and verified.** All 9 epics below are built and all 41 test cases pass (regression + every epic) against `poultary.localhost`. The permanent, repeatable version of these test cases lives at `ob_poultry/ob_poultry/tests/test_poultry_module.py` (an `IntegrationTestCase`, runnable via `bench run-tests`) — the tables below stay as the human-readable spec and success-criteria reference; treat the test file as the source of truth if the two ever drift.

Execution breakdown of [FRD.md](./FRD.md) §2 (gap closure), organized as epics. Each epic lists build tasks, then test cases with a concrete pass/fail success criterion. Epic 0 is a regression safety net over what already exists (FRD §1) — run it before and after every other epic, since most new work touches `Poultry Batch.recalculate_performance()` (renamed from `recalculate_bird_count()` when FCR/CFCR were added) and `Poultry Daily Log`, the two places most exposed to drift.

Test cases assume ERPNext's Setup Wizard has been completed on the target site (Company, Item Group, UOM, at least one Warehouse) — a prerequisite noted in the BRD's assumptions, not something these tests set up themselves.

## Epic 0 — Regression safety net (as-built)

### Tasks

- [x] Script the smoke sequence below as a repeatable check (console script or test module) so it can be re-run after every later epic, not just once.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-REG-01 | Batch creation seeds bird count | Create a `Poultry Shed` (capacity 5000), a `Poultry Breed`, a `Poultry Batch` with `initial_bird_count = 1000` | `current_bird_count == 1000` immediately after insert |
| TC-REG-02 | Shed capacity is enforced | Create a batch with `initial_bird_count` greater than its shed's `capacity` | Insert is rejected with a `ValidationError` naming the shed |
| TC-REG-03 | Daily log submit reduces bird count | Submit a `Poultry Daily Log` with `mortality_count = 5`, `cull_count = 1` against a 1000-bird batch | Batch `current_bird_count == 994`, `total_mortality == 5` |
| TC-REG-04 | Duplicate same-day log is blocked | Submit a second log for the same `batch` + `log_date` | Rejected with a `ValidationError` naming the existing log |
| TC-REG-05 | Cancel reverses the count | Cancel the log from TC-REG-03 | Batch `current_bird_count` returns to `1000`, `total_mortality` returns to `0` |
| TC-REG-06 | Over-mortality is blocked | Submit a log whose mortality + cull, added to existing submitted totals, exceeds `initial_bird_count` | Rejected with a `ValidationError` stating the total would exceed the initial count |
| TC-REG-07 | Feed consumption posts a Stock Entry | Set `batch.feed_warehouse`, submit a log with `feed_item` + `feed_consumed_kg = 25` | A submitted Stock Entry (Material Issue) exists, linked back via `log.stock_entry`; warehouse balance drops by 25 |
| TC-REG-08 | Cancel reverses the Stock Entry | Cancel the log from TC-REG-07 | The linked Stock Entry is cancelled; warehouse balance is restored |
| TC-REG-09 | Formula &rarr; BOM &rarr; Work Order | Create a `Poultry Feed Formula` with 3 ingredients, call `create_or_update_bom()` then `make_work_order(50)` | A submitted BOM exists matching the ingredient list; a Work Order exists for qty 50 against that BOM |

## Epic 1 — Cause-coded mortality (FRD §2.2)

### Tasks

- [x] Add child doctype `Poultry Daily Log Mortality Entry` (`cause`, `sex`, `count`, `description`).
- [x] Add `mortality_details` table field to `Poultry Daily Log`.
- [x] Make `mortality_count` read-only; compute it as `sum(mortality_details.count)` in `validate()`.
- [x] Confirm `validate_bird_count()` and `Poultry Batch.recalculate_bird_count()` still read the (now-computed) `mortality_count` column correctly — no SQL changes expected.
- [x] Data migration: existing rows with a manually-entered `mortality_count` and no `mortality_details` keep their stored value (don't zero out history).

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-MORT-01 | Count rolls up from detail rows | Add two `mortality_details` rows (`Disease`, count 3) and (`Heat Stress`, count 2) to a log | `mortality_count == 5` after `validate()`, without being typed in directly |
| TC-MORT-02 | Empty detail table means zero | Save a log with no `mortality_details` rows | `mortality_count == 0`, no error |
| TC-MORT-03 | Rollup still respects the batch cap | Add detail rows whose sum, combined with other submitted logs, exceeds `initial_bird_count` | Rejected, same message as TC-REG-06 |
| TC-MORT-04 | Historical rows are untouched | Load a pre-migration log with a stored `mortality_count` and no detail rows | `mortality_count` still displays its original stored value |

## Epic 2 — Graded egg production + HDEP (FRD §2.1)

### Tasks

- [x] Add child doctype `Poultry Daily Log Egg Entry` (`grade`, `opening_count`, `production_count`, `closing_count`, `avg_weight_g`).
- [x] Add `egg_entries` table field to `Poultry Daily Log`.
- [x] On `validate()`, fetch each grade's `opening_count` from the prior day's `closing_count` for the same batch (0 if none), and compute `closing_count = opening_count + production_count`.
- [x] Add read-only `total_eggs_produced` (sum of `production_count`) and `hdep_percent` to `Poultry Daily Log`.
- [x] Mark `egg_count` deprecated and read-only; stop writing to it from new logs.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-EGG-01 | Opening carries from prior day | Log Day 1 with `Table Egg` production 200 (closing 200); log Day 2 with `Table Egg` production 150 | Day 2's `Table Egg` row has `opening_count == 200`, `closing_count == 350` |
| TC-EGG-02 | First-ever entry has zero opening | Submit the first-ever log for a batch with a `Hatching Egg` row | `opening_count == 0` |
| TC-EGG-03 | Total rolls up across grades | Log 3 grade rows with production 100/50/10 | `total_eggs_produced == 160` |
| TC-EGG-04 | HDEP computed against current bird count | With `batch.current_bird_count == 1000` and `total_eggs_produced == 800` | `hdep_percent == 80` (within rounding) |
| TC-EGG-05 | HDEP is safe at zero birds | Compute HDEP for a batch with `current_bird_count == 0` | `hdep_percent == 0`, no divide-by-zero error |

## Epic 3 — Standard benchmarks (FRD §2.3)

### Tasks

- [x] Add `Poultry Benchmark` master (`breed`, `age_in_days`, `standard_mortality_pct`, `standard_feed_per_bird_g`, `standard_body_weight_g`, `standard_fcr`).
- [x] Enforce `(breed, age_in_days)` uniqueness in `validate()`.
- [x] Add `std_mortality_pct`, `std_feed_per_bird_g`, `std_body_weight_g` read-only fields to `Poultry Daily Log`, resolved from the nearest benchmark row &le; the batch's current age.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-BMK-01 | Duplicate breed+age is blocked | Create two `Poultry Benchmark` rows for the same breed and `age_in_days` | Second insert rejected |
| TC-BMK-02 | Exact-age match is used | Create a benchmark at `age_in_days = 10`; submit a log when the batch is exactly 10 days old | Log's `std_*` fields match the benchmark row |
| TC-BMK-03 | Nearest-earlier match is used | Create a benchmark only at `age_in_days = 7`; submit a log at day 9 | Log's `std_*` fields fall back to the day-7 benchmark |
| TC-BMK-04 | No benchmark exists | Submit a log for a breed with zero benchmark rows | `std_*` fields stay blank; no error |

## Epic 4 — FCR / CFCR (FRD §2.4)

### Tasks

- [x] Add `cumulative_feed_kg`, `fcr`, `cfcr` read-only fields to `Poultry Batch`.
- [x] Rename/extend `recalculate_bird_count()` to `recalculate_performance()`, called from the same `Poultry Daily Log` submit/cancel hooks, computing all four derived fields (existing two plus these three) in one pass.
- [x] Document the CFCR approximation (mortality valued at latest average body weight) inline in the docstring, matching FRD §2.4's flag for operations sign-off.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-FCR-01 | Cumulative feed sums correctly | Submit 3 logs with `feed_consumed_kg` 100, 120, 110 | `cumulative_feed_kg == 330` |
| TC-FCR-02 | FCR uses latest body weight | Submit logs ending with `average_body_weight_g = 2000` on a batch of 900 current birds, cumulative feed 3240 kg | `fcr == 1.8` (3240 &divide; (900 &times; 2.0)) |
| TC-FCR-03 | CFCR diverges from FCR once there's mortality | Same batch as TC-FCR-02 but with `total_mortality > 0` | `cfcr <= fcr` and `cfcr != fcr` — **resolved during implementation**: the FRD §2.4 formula folds mortality weight into the *denominator* (`feed &divide; (live_weight + mortality_weight)`), so a bigger denominator against the same feed total makes CFCR the *lower* of the two, not higher. Confirmed against a real run: `fcr=1.82, cfcr=1.8`. If farm operations' actual convention expects the opposite direction, that's a formula change to revisit, not a bug in this test. |
| TC-FCR-04 | Zero birds is safe | Compute FCR/CFCR for a batch with `current_bird_count == 0` and no submitted logs | Both `0`, no divide-by-zero error |

## Epic 5 — Vaccination scheduling (FRD §2.5)

### Tasks

- [x] Add `Poultry Vaccination Schedule Template` master + `Poultry Vaccination Schedule Item` child table.
- [x] Add `Poultry Vaccination Due` standalone doctype.
- [x] On `Poultry Batch` insert, bulk-create `Poultry Vaccination Due` rows from the breed's active template (if one exists), with `due_date = start_date + age_in_days`.
- [x] Add optional `due` link field to `Poultry Vaccination Record`; on save, mark the linked Due row `Done` and back-fill `vaccination_record`.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-VAC-01 | Due list generated on placement | Create an active template with 3 items for a breed; create a batch of that breed | Exactly 3 `Poultry Vaccination Due` rows exist for the batch, `due_date` correctly offset from `start_date` |
| TC-VAC-02 | No template, no due rows, no error | Create a batch for a breed with no active template | Batch insert succeeds; zero Due rows created |
| TC-VAC-03 | Recording against a due item closes it | Create a `Poultry Vaccination Record` with `due` set to a Pending row | The Due row's `status` becomes `Done`, `vaccination_record` is set to the new record's name |
| TC-VAC-04 | Ad hoc recording still works | Create a `Poultry Vaccination Record` with no `due` set | Insert succeeds exactly as today; no Due row is affected |
| TC-VAC-05 | Existing next-due-date validation still holds | Create a record with `next_due_date <= date_given` | Rejected, same as TC-REG-level existing behavior |

## Epic 6 — Feed formula ingredient categories (FRD §2.6)

### Tasks

- [x] Add `category` Select field (Raw Material / Medicine, default Raw Material) to `Poultry Feed Formula Ingredient`.
- [x] Add `raw_material_total_kg`, `medicine_total_kg` read-only rollups to `Poultry Feed Formula`, computed in `calculate_percentages()`.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-CAT-01 | Totals split by category | Formula with 2 "Raw Material" rows (60kg, 30kg) and 1 "Medicine" row (2kg) | `raw_material_total_kg == 90`, `medicine_total_kg == 2` |
| TC-CAT-02 | Default category is Raw Material | Add an ingredient row without setting `category` | Saved row has `category == "Raw Material"` |
| TC-CAT-03 | Percentage calc is unaffected | Same formula as TC-CAT-01 with `batch_size_kg = 100` | Each row's `percentage` still computed as before (60%, 30%, 2%) — category change doesn't alter existing behavior |

## Epic 7 — Feed Production yield & cost (FRD §2.7)

### Tasks

- [x] Add `Poultry Feed Production` doctype (`formula`, `planned_batches`, `planned_qty_kg`, `work_order`, `actual_output_kg`, `yield_percent`, `cost_per_kg`).
- [x] Implement `create_work_order()` on `Poultry Feed Production`, reusing the existing BOM-creation path from `Poultry Feed Formula`.
- [x] Implement yield computation once `actual_output_kg` is entered. `cost_per_kg` deliberately stays unset for now — see FRD §2.7's note that it depends on completed Work Order costing that isn't wired up yet; not approximated.
- [x] `Poultry Feed Formula.make_work_order()` kept as-is (still used directly by `Poultry Feed Production.create_work_order()`'s BOM-creation step) rather than removed — no other caller existed to migrate, and removing a working, tested method for no functional gain wasn't worth it.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-PROD-01 | Planned qty derives from formula | Create a Feed Production with `planned_batches = 5` against a formula with `batch_size_kg = 100` | `planned_qty_kg == 500` |
| TC-PROD-02 | Work Order is created correctly | Call `create_work_order()` | A submitted/draft Work Order exists with `qty == planned_qty_kg` against the formula's BOM |
| TC-PROD-03 | Yield computes correctly | Set `actual_output_kg = 510` against `planned_qty_kg = 500` | `yield_percent == 102` |
| TC-PROD-04 | Missing actual output leaves yield blank | Save a Feed Production with `actual_output_kg` unset | `yield_percent` stays blank, no error |

## Epic 8 — Roles & permissions (FRD §2.8)

### Tasks

- [x] Create roles: `Poultry Manager`, `Poultry Attendant`, `Vaccination In-charge`, `Feed Mill Operator`.
- [x] Update every Poultry doctype's `permissions` block per the FRD §2.8 matrix, keeping `System Manager` as the full-access fallback on all of them.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-ROLE-01 | Attendant can log, can't close a batch | As a user with only `Poultry Attendant`, create a `Poultry Daily Log`; then attempt `close_batch()` on a `Poultry Batch` | Log creation succeeds; `close_batch()` raises a `PermissionError` |
| TC-ROLE-02 | Attendant has read-only Shed/Breed/Batch | As `Poultry Attendant`, attempt to edit a `Poultry Shed` | Rejected with a `PermissionError` |
| TC-ROLE-03 | Vaccination In-charge scope | As a user with only `Vaccination In-charge`, create a `Poultry Vaccination Record`; attempt to edit a `Poultry Batch` | Record creation succeeds; batch edit is rejected |
| TC-ROLE-04 | Feed Mill Operator scope | As `Feed Mill Operator`, create/edit a `Poultry Feed Formula`; attempt to edit a `Poultry Batch` | Formula edit succeeds; batch edit is rejected |
| TC-ROLE-05 | System Manager is unaffected | As `System Manager`, perform one write on every Poultry doctype | All succeed, matching pre-Epic-8 behavior |

## Epic 9 — Closed-batch guard (fix flagged in FIT-GAP, BR-FLK-11)

### Tasks

- [x] Add a check to `Poultry Daily Log.validate()`: reject if `batch.status == "Closed"`.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-CLOSE-01 | Closed batch rejects new logs | Close a batch via `close_batch()`, then attempt to create a `Poultry Daily Log` against it | Rejected with a `ValidationError` naming the closed batch |
| TC-CLOSE-02 | Open batch is unaffected | Create a log against a batch still `Active` | Succeeds exactly as before |

## Epic 10 — Workspace, sidebar, and desktop icon (shipping polish, not in the original FRD)

Requested after the epics above were implemented and verified, so the module is actually reachable from Desk rather than only by direct doctype URL.

### Tasks

- [x] Add a `Workspace` (`ob_poultry/poultry/workspace/poultry/poultry.json`) — header, 4 shortcuts (Batch list, new Daily Log, Vaccination Due list, Feed Formula list), and 3 link cards (Flock Management, Vaccination, Feed Mill) covering all 10 non-child doctypes.
- [x] Add a `Workspace Sidebar` (`ob_poultry/workspace_sidebar/poultry.json`) — same structure as a left-nav tree, sectioned the same way.
- [x] Add a `Desktop Icon` (`ob_poultry/desktop_icon/poultry.json`) linking to the Workspace Sidebar, so Poultry appears as its own top-level app tile.
- [x] Verified every `icon` value referenced (`bird`, `home`, `list-tree`, `calendar`, `target`, `syringe`, `factory`) actually exists in this Frappe version's bundled icon sets before using it — `chicken` was the first choice and doesn't exist anywhere in the bundle, caught before shipping.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-WS-01 | Workspace registers correctly | Migrate, then query `Workspace` "Poultry" | Exists, `module == "Poultry"`, `public == 1`, 13 links, 4 shortcuts |
| TC-WS-02 | Sidebar registers correctly | Query `Workspace Sidebar` "Poultry" | Exists, 13 items covering all 10 non-child doctypes plus the Home/Workspace link |
| TC-WS-03 | Desktop icon registers correctly | Query `Desktop Icon` "Poultry" | Exists, `link_to == "Poultry"`, `link_type == "Workspace Sidebar"` |

## Epic 11 — Per-day mortality % (FRD §3.1)

### Tasks

- [ ] Add read-only `daily_mortality_pct` (Percent) to `Poultry Daily Log`.
- [ ] Compute it in `validate()`: `mortality_count &divide; batch.current_bird_count &times; 100`, `0` when `current_bird_count` is `0`.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-DMP-01 | Computed correctly | Batch with `current_bird_count = 1000`, log with `mortality_details` summing to 5 | `daily_mortality_pct == 0.5` |
| TC-DMP-02 | Safe at zero birds | Log against a batch with `current_bird_count == 0` | `daily_mortality_pct == 0`, no divide-by-zero error |

## Epic 12 — Double Yolk grade + tray counts (FRD §3.2)

### Tasks

- [ ] Add `Double Yolk` to `Poultry Daily Log Egg Entry.grade`'s Select options.
- [ ] Add Single doctype `Poultry Settings` with `eggs_per_tray` (Int, default 30).
- [ ] Add read-only `trays` (Float) to `Poultry Daily Log Egg Entry`, computed in `compute_egg_rollup()` as `production_count &divide; eggs_per_tray`.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-TRAY-01 | Double Yolk accepted as a grade | Submit a log with an egg entry `grade = "Double Yolk"` | Insert succeeds, row saved with that grade |
| TC-TRAY-02 | Trays computed from default setting | `Poultry Settings.eggs_per_tray` at default 30, egg entry `production_count = 300` | `trays == 10` |
| TC-TRAY-03 | Trays respect a changed setting | Set `eggs_per_tray = 20`, submit a log with `production_count = 300` | `trays == 15` |

## Epic 13 — Feed logged in an alternate unit (FRD §3.3)

### Tasks

- [ ] Add `feed_uom` (Link &rarr; UOM) and `feed_qty` (Float) to `Poultry Daily Log`.
- [ ] In `validate()`, before `create_feed_stock_entry()` runs on submit: if both are set, compute `feed_consumed_kg` via `erpnext.stock.get_item_details.get_conversion_factor(feed_item, feed_uom)`.
- [ ] Confirm existing behavior (direct `feed_consumed_kg` entry, `feed_uom` blank) is completely unaffected — this must be provably backward compatible.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-UOM-01 | Bag quantity converts to kg | Item with a UOM Conversion Detail row `Bag = 50 Kg`; log with `feed_uom = "Bag"`, `feed_qty = 3` | `feed_consumed_kg == 150` |
| TC-UOM-02 | Blank feed_uom is unchanged (regression) | Log with `feed_consumed_kg = 25` set directly, `feed_uom` blank | `feed_consumed_kg` stays `25`, Stock Entry posts exactly as before this epic |
| TC-UOM-03 | Feeds into Stock Entry correctly | Log with `feed_uom`/`feed_qty` set, submit | Linked Stock Entry's `qty` equals the converted `feed_consumed_kg`, not the raw `feed_qty` |

## Epic 14 — Feed cost per batch/date (FRD §3.4, report only)

### Tasks

- [ ] Extend `poultry_feed_consumption_report.py` to join `Stock Entry Detail` on `Poultry Daily Log.stock_entry` and add a `feed_cost` column.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-FCOST-01 | Cost pulled from real valuation | Submit a feed-consuming log against stock with a known valuation rate | Report's `feed_cost` column matches `Stock Entry Detail.amount` for that entry exactly |
| TC-FCOST-02 | No stock entry, no cost shown | A log with `feed_consumed_kg` unset (no stock entry created) | Report row shows blank/zero cost, not an error |

## Epic 15 — Production cost per egg (FRD §3.5, report only)

### Tasks

- [ ] New report `Poultry Egg Production Cost`: per batch/date range, `sum(feed_cost) / sum(total_eggs_produced)`.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-EPC-01 | Computed correctly | Batch with feed cost 1000 and 200 eggs produced in range | Report shows cost/egg `== 5` |
| TC-EPC-02 | Safe with zero eggs | Batch with feed cost but zero eggs produced (e.g. a broiler batch) | Cost/egg blank or `0`, not a divide-by-zero error |

## Epic 16 — Daily expenses (FRD §3.6)

### Tasks

- [ ] Add child doctype `Poultry Daily Log Expense` (`description`, `amount`).
- [ ] Add `expenses` table field and read-only `total_expenses` rollup to `Poultry Daily Log`.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-EXP-01 | Total rolls up | Log with two expense rows, 500 and 668 | `total_expenses == 1168` |
| TC-EXP-02 | Empty is zero | Log with no expense rows | `total_expenses == 0`, no error |

## Epic 17 — Egg sales (FRD §3.7)

### Tasks

- [ ] Add `Poultry Egg Sale` (submittable) and `Poultry Egg Sale Item` (child) doctypes.
- [ ] Implement the per-grade available-balance validation (cumulative production minus cumulative other sold, mirroring `Poultry Chick Transfer.validate_against_hatch()`).
- [ ] New/extended report showing net egg stock (production minus sales) per batch and grade.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-SALE-01 | Sale within available stock succeeds | Batch has produced 500 Table Eggs; sell 200 | Insert and submit succeed, `total_amount` computed correctly from `quantity &times; rate` |
| TC-SALE-02 | Over-selling is blocked | Same batch, attempt to sell 400 more (600 total against 500 produced) | Rejected with a `ValidationError` naming the batch and grade |
| TC-SALE-03 | Net stock report reflects sales | After TC-SALE-01, run the net-stock report for that batch/grade | Shows `300` remaining (500 produced &minus; 200 sold) |
| TC-SALE-04 | Daily Log ledger untouched by sales | Before/after TC-SALE-01, compare the batch's `Poultry Daily Log Egg Entry.closing_count` for that date/grade | Unchanged — sales never mutate a submitted Daily Log |

## Epic 18 — Shed default feed warehouse (FRD §3.8)

### Tasks

- [ ] Add `default_feed_warehouse` (Link &rarr; Warehouse) to `Poultry Shed`.
- [ ] In `Poultry Batch.validate()`, default `feed_warehouse` from the shed's default when the batch is new and `feed_warehouse` is blank.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-DWH-01 | Default applied on new batch | Shed with `default_feed_warehouse` set; create a batch in that shed with `feed_warehouse` left blank | Batch's `feed_warehouse` is populated from the shed's default after insert |
| TC-DWH-02 | Explicit choice is never overridden | Create a batch in the same shed, explicitly setting a *different* `feed_warehouse` | That explicit value is kept, not overwritten by the shed's default |
| TC-DWH-03 | No default, no error | Shed with `default_feed_warehouse` blank; create a batch with `feed_warehouse` also blank | Insert succeeds, `feed_warehouse` stays blank (existing behavior, e.g. feed logging will ask for it later) |

## Epic 19 — Daily operational dashboard (from customer's own field list, 2026-09-28)

A second piece of customer evidence (a plain list of what they enter daily vs. what they want to see on a dashboard) confirmed Epics 11-18 above and added two things: **"Dirty Egg"** as a grade distinct from damage/cracked (soiled shell, not broken), and an explicit ask for farm-wide daily totals to be visible without opening a report.

### Tasks

- [ ] Add `Dirty Egg` to `Poultry Daily Log Egg Entry.grade`'s options, alongside `Double Yolk` from Epic 12.
- [ ] Add `feed_per_bird_g` (Float, read-only) to `Poultry Daily Log` — `feed_consumed_kg * 1000 / batch.current_bird_count`, same zero-guard pattern as everywhere else.
- [ ] Add `damage_pct` (Percent, read-only) to `Poultry Daily Log` — damaged egg count (grades Cracked/Waste/Dirty) &divide; `total_eggs_produced` &times; 100.
- [ ] Add 4 new Number Cards to the Poultry workspace, each using a dynamic "Today" date filter: **Eggs Produced Today** (sum `total_eggs_produced` where `log_date = Today`), **Feed Consumed Today (Kg)** (sum `feed_consumed_kg` where `log_date = Today`), **Mortality Today** (sum `mortality_count` where `log_date = Today`), **Culled Today** (sum `cull_count` where `log_date = Today`).
- [ ] Confirm Age (already computed per-log via `date_diff`), Bird Closing Stock (`current_bird_count`), and Shed Tray Stock (closing `trays` from Epic 12) are all visible on the Batch/Daily Log forms — batch-level and ratio metrics (age in weeks, damage %, tray stock) don't reduce to a single farm-wide Number Card, so they stay on the record itself rather than being forced into the dashboard.

### Test cases

| ID | Scenario | Steps | Success criteria |
|---|---|---|---|
| TC-DASH-01 | Dirty Egg accepted as a grade | Submit a log with an egg entry `grade = "Dirty Egg"` | Insert succeeds |
| TC-DASH-02 | Feed per bird computed | `feed_consumed_kg = 100`, `current_bird_count = 1000` | `feed_per_bird_g == 100` |
| TC-DASH-03 | Damage % computed | Total eggs produced 500, 20 of them Cracked/Waste/Dirty combined | `damage_pct == 4` |
| TC-DASH-04 | Today's Number Cards reflect only today | Submit logs for yesterday and today with different egg/feed/mortality/cull values | Each Number Card's value matches only today's sum, not yesterday's |

## Definition of done

An epic is done when every task is checked, every test case above passes, and Epic 0's regression suite still passes unchanged (proving the new work didn't disturb bird-count or stock-entry correctness). `uv run ruff check` (or this app's own `ruff check`, per its `pyproject.toml`) is clean before any epic is considered mergeable.

All of the above held at time of writing: 41/41 test cases pass (Epics 0–9, permanent version at `ob_poultry/ob_poultry/tests/test_poultry_module.py`), and Epic 10's three records were confirmed present with correct counts after a clean `migrate`.
