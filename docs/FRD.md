# Functional Requirements Document — Poultry Module

Doctype-level specification. **As-built** sections document what exists today (module `Poultry`, path `ob_poultry/ob_poultry/poultry/doctype/`) so this document is self-contained. **Proposed** sections close the gaps identified in [FIT_GAP_ANALYSIS.md](./FIT_GAP_ANALYSIS.md). Every item cites the `BR-*` it satisfies.

## 1. As-built doctypes

### 1.1 Poultry Shed — *BR-FLK-01*

Master. Autoname `field:shed_name`.

| Field | Type | Rule |
|---|---|---|
| `shed_name` | Data, required, unique | primary identifier |
| `capacity` | Int | max birds this shed can hold |
| `location` | Data | free text |
| `is_active` | Check, default 1 | |

Validation: `capacity` must not be negative.

### 1.2 Poultry Breed — *BR-FLK-02*

Master. Autoname `field:breed_name`.

| Field | Type | Rule |
|---|---|---|
| `breed_name` | Data, required, unique | |
| `breed_type` | Select, required — Broiler / Layer / Breeder / Dual Purpose | |
| `standard_fcr` | Float | target FCR for the breed; currently stored, not yet consumed (§2.2 closes this) |
| `description` | Small Text | |

### 1.3 Poultry Batch — *BR-FLK-03, BR-FLK-04, BR-FLK-11*

Transaction (not submittable). Autoname `format:PB-{YYYY}-{#####}`.

| Field | Type | Rule |
|---|---|---|
| `shed` | Link &rarr; Poultry Shed, required | |
| `breed` | Link &rarr; Poultry Breed, required | |
| `breed_type` | Select, read-only | fetched from `breed.breed_type` |
| `start_date` | Date, required, default Today | |
| `status` | Select, read-only — Active / Closed, default Active | set only via `close_batch()` |
| `end_date` | Date, read-only | set by `close_batch()` |
| `initial_bird_count` | Int, required | |
| `current_bird_count` | Int, read-only | derived, see below |
| `total_mortality` | Int, read-only | derived, see below |
| `feed_warehouse` | Link &rarr; Warehouse | source warehouse for daily feed issue |
| `source` | Data | hatchery/supplier name |
| `notes` | Small Text | |

Business rules:

- `validate_shed_capacity()` rejects `initial_bird_count > shed.capacity`.
- On insert, `current_bird_count` defaults to `initial_bird_count`.
- `recalculate_bird_count()` — called by `Poultry Daily Log` on submit/cancel — sums `mortality_count` + `cull_count` across all **submitted** `Poultry Daily Log` rows for this batch, and sets `total_mortality` and `current_bird_count = initial_bird_count - total_removed` via `frappe.db.set_value` (cached derived values, not independently editable — single source of truth is the daily log ledger).
- `close_batch()` (whitelisted) — rejects if already Closed; otherwise sets `status = Closed`, `end_date = end_date or today`.

### 1.4 Poultry Daily Log — *BR-FLK-05 through BR-FLK-08*

Transaction, **submittable**. Autoname `format:PDL-{YYYY}-{#####}`.

| Field | Type | Rule |
|---|---|---|
| `batch` | Link &rarr; Poultry Batch, required | |
| `log_date` | Date, required, default Today | |
| `mortality_count` | Int, default 0 | |
| `cull_count` | Int, default 0 | |
| `average_body_weight_g` | Float | |
| `water_consumed_liters` | Float | |
| `feed_item` | Link &rarr; Item | |
| `feed_consumed_kg` | Float | |
| `stock_entry` | Link &rarr; Stock Entry, read-only | set on submit |
| `egg_count` | Int | flat count, see §2.1 for grade breakdown |
| `notes` | Small Text | |

Business rules:

- `validate_unique_log()` — one log per `batch` + `log_date`.
- `validate_bird_count()` — sums mortality+cull across other submitted logs for the batch, adds this row's values, rejects if the total exceeds `batch.initial_bird_count`.
- `on_submit()` — calls `create_feed_stock_entry()` then `batch.recalculate_bird_count()`.
- `create_feed_stock_entry()` — if `feed_consumed_kg` is set, requires `feed_item` and `batch.feed_warehouse`; posts a Stock Entry (`stock_entry_type = Material Issue`, `company` derived from the warehouse's own company, one line: `feed_item` / `feed_consumed_kg` / `s_warehouse = batch.feed_warehouse`), submits it, stores its name on `stock_entry`.
- `on_cancel()` — cancels the linked Stock Entry if still submitted, then recalculates the batch.

### 1.5 Poultry Vaccination Record — *BR-VAC-03*

Transaction (not submittable). Autoname `format:PVR-{YYYY}-{#####}`.

| Field | Type | Rule |
|---|---|---|
| `batch` | Link &rarr; Poultry Batch, required | |
| `vaccine_name` | Data, required | |
| `dose` | Data | |
| `date_given` | Date, required, default Today | |
| `next_due_date` | Date | |
| `administered_by` | Data | |
| `notes` | Small Text | |

Validation: `next_due_date`, if set, must be after `date_given`.

### 1.6 Poultry Feed Formula — *BR-FED-01, BR-FED-03*

Master. Autoname `field:feed_name`.

| Field | Type | Rule |
|---|---|---|
| `feed_name` | Data, required, unique | |
| `feed_item` | Link &rarr; Item, required | the finished good this formula produces |
| `batch_size_kg` | Float, required, default 100 | recipe basis |
| `is_active` | Check, default 1 | |
| `ingredients` | Table &rarr; Poultry Feed Formula Ingredient, required | |
| `bom` | Link &rarr; BOM, read-only | set by `create_or_update_bom()` |

Business rules:

- `calculate_percentages()` — sets each ingredient's `percentage = quantity_kg / batch_size_kg * 100`.
- `create_or_update_bom()` (whitelisted) — builds or updates an ERPNext BOM (`item = feed_item`, `quantity = batch_size_kg`, one BOM Item row per ingredient), submits it, stores the BOM name.
- `make_work_order(planned_qty)` (whitelisted) — creates a Work Order against the stored BOM for `planned_qty`, company resolved via `get_default_company()` (user default &rarr; global default &rarr; first Company, else throws).

### 1.7 Poultry Feed Formula Ingredient — *BR-FED-01*

Child table (`istable: 1`) of Poultry Feed Formula.

| Field | Type | Rule |
|---|---|---|
| `raw_material` | Link &rarr; Item, required | |
| `quantity_kg` | Float, required | |
| `percentage` | Percent, read-only | computed by the parent |

## 2. Proposed doctypes and changes (gap closure)

### 2.1 Egg grading on Poultry Daily Log — *BR-EGG-01, BR-EGG-02*

Add a child table `egg_entries` (options: new child doctype **Poultry Daily Log Egg Entry**):

| Field | Type | Rule |
|---|---|---|
| `grade` | Select, required — Hatching Egg / Table Egg / Jumbo Egg / Cracked Egg / Waste Egg | |
| `opening_count` | Int, read-only | fetched from the previous day's `closing_count` for the same batch+grade; 0 if none |
| `production_count` | Int, required | entered |
| `closing_count` | Int, read-only | `opening_count + production_count` |
| `avg_weight_g` | Float | |

On `Poultry Daily Log`, replace `egg_count` with a read-only rollup `total_eggs_produced` (sum of `production_count` across `egg_entries`, computed in `validate()`), and add `hdep_percent` (Percent, read-only): `total_eggs_produced / batch.current_bird_count * 100` (0 if the batch has no birds). **Migration note:** `egg_count` stays on the doctype as a deprecated, no-longer-editable field for one release rather than being dropped outright, so historical rows aren't silently zeroed.

### 2.2 Cause-coded mortality on Poultry Daily Log — *BR-FLK-06*

Add a child table `mortality_details` (options: new child doctype **Poultry Daily Log Mortality Entry**):

| Field | Type | Rule |
|---|---|---|
| `cause` | Select, required — Disease / Injury / Heat Stress / Culled (Runt or Weak) / Predator / Unknown / Other | |
| `sex` | Select — Male / Female / Unspecified, default Unspecified | |
| `count` | Int, required | |
| `description` | Small Text | free text, e.g. specific disease name |

`mortality_count` stays on the parent as a read-only rollup (`sum(count)` across `mortality_details`), computed in `validate()`, so `Poultry Batch.recalculate_bird_count()`'s existing SQL (which reads `mortality_count`/`cull_count` columns directly) needs no change. `cull_count` stays a flat entry field — culls are a management decision, not a cause code, and don't need the breakdown.

### 2.3 Poultry Benchmark (new master) — *BR-FLK-10*

| Field | Type | Rule |
|---|---|---|
| `breed` | Link &rarr; Poultry Breed, required | |
| `age_in_days` | Int, required | |
| `standard_mortality_pct` | Percent | cumulative, as of this age |
| `standard_feed_per_bird_g` | Float | daily |
| `standard_body_weight_g` | Float | |
| `standard_fcr` | Float | cumulative, as of this age |

Validation: `(breed, age_in_days)` must be unique — checked in `validate()` since Frappe has no native composite-unique constraint. `Poultry Daily Log` gains three read-only fields (`std_mortality_pct`, `std_feed_per_bird_g`, `std_body_weight_g`) populated by looking up the `Poultry Benchmark` row for the batch's breed at the batch's current age in days (nearest age &le; current, if an exact match isn't entered); left blank with no error if no benchmark row exists for that breed/age yet.

### 2.4 FCR / CFCR on Poultry Batch — *BR-FLK-09*

Add read-only fields `cumulative_feed_kg`, `fcr`, `cfcr` to `Poultry Batch`, recomputed alongside `recalculate_bird_count()` (rename the method `recalculate_performance()` to cover both):

- `cumulative_feed_kg` = sum of `feed_consumed_kg` across submitted `Poultry Daily Log` rows for the batch.
- `fcr` = `cumulative_feed_kg &divide; total_live_weight_kg`, where `total_live_weight_kg = current_bird_count &times; (latest submitted average_body_weight_g &divide; 1000)`.
- `cfcr` = `cumulative_feed_kg &divide; (total_live_weight_kg + mortality_weight_kg)`, where `mortality_weight_kg = total_mortality &times; (latest submitted average_body_weight_g &divide; 1000)` — an approximation that assumes birds died at roughly the flock's current average weight, since the reference system's cause-level entries don't carry a per-death weight either. **Flagged for confirmation with farm operations before CFCR is used in any contract or payout calculation** — the standard formula varies by operation and this is a reasonable v1 approximation, not a verified industry figure.

Both are `0` (not an error) when `current_bird_count` is 0 or no daily log has been submitted yet.

### 2.5 Vaccination scheduling — *BR-VAC-01, BR-VAC-02*

**Poultry Vaccination Schedule Template** (new master):

| Field | Type | Rule |
|---|---|---|
| `breed` | Link &rarr; Poultry Breed, required | |
| `template_name` | Data, required | |
| `is_active` | Check, default 1 | |
| `items` | Table &rarr; Poultry Vaccination Schedule Item, required | |

**Poultry Vaccination Schedule Item** (child table):

| Field | Type | Rule |
|---|---|---|
| `age_in_days` | Int, required | |
| `vaccine_name` | Data, required | |
| `dose` | Data | |
| `method` | Select — SubCutaneous / Intramuscular / Eye Drop / Beak Dip / Drinking Water / Spray / Wing Web / Other | |
| `description` | Small Text | |

**Poultry Vaccination Due** (new standalone doctype, not a child table — needs its own identity so a `Poultry Vaccination Record` can point back at exactly one due item):

| Field | Type | Rule |
|---|---|---|
| `batch` | Link &rarr; Poultry Batch, required | |
| `age_in_days` | Int, read-only | copied from the template item |
| `due_date` | Date, read-only | `batch.start_date + age_in_days` |
| `vaccine_name`, `dose`, `method` | as template | read-only, copied from the template item |
| `status` | Select — Pending / Done / Skipped, default Pending | |
| `vaccination_record` | Link &rarr; Poultry Vaccination Record, read-only | set when fulfilled |

Business rule: on `Poultry Batch` insert, if an active `Poultry Vaccination Schedule Template` exists for the batch's breed, bulk-create one `Poultry Vaccination Due` row per template item. `Poultry Vaccination Record` gains an optional field `due` (Link &rarr; Poultry Vaccination Due); on save, if set, the linked Due row's `status` is set to `Done` and `vaccination_record` is back-filled. A batch with no matching template simply gets no due rows — administration can still be recorded ad hoc, exactly as today.

### 2.6 Ingredient category on Poultry Feed Formula Ingredient — *BR-FED-02*

Add `category` (Select, required, default "Raw Material" — Raw Material / Medicine) to `Poultry Feed Formula Ingredient`. Add two read-only rollups to `Poultry Feed Formula`: `raw_material_total_kg`, `medicine_total_kg`, summed by category in `calculate_percentages()`.

### 2.7 Poultry Feed Production (new doctype, wraps Work Order) — *BR-FED-04, BR-FED-05*

| Field | Type | Rule |
|---|---|---|
| `formula` | Link &rarr; Poultry Feed Formula, required | |
| `planned_batches` | Float, required | the batch-count multiplier |
| `planned_qty_kg` | Float, read-only | `formula.batch_size_kg &times; planned_batches` |
| `work_order` | Link &rarr; Work Order, read-only | created by `create_work_order()` |
| `actual_output_kg` | Float | entered once the linked Work Order completes |
| `yield_percent` | Percent, read-only | `actual_output_kg &divide; planned_qty_kg &times; 100` |
| `cost_per_kg` | Currency, read-only | fetched from the Work Order's total actual cost &divide; `actual_output_kg` once both are known |

`Poultry Feed Formula.make_work_order()` is superseded by `Poultry Feed Production.create_work_order()`, which does the same Work Order creation but returns a `Poultry Feed Production` record instead of a bare Work Order name — giving the Feed Mill Operator a poultry-native production log with yield/cost visible without opening ERPNext's Manufacturing workspace (BR-SYS-01 still holds: the Work Order itself remains the actual execution engine).

### 2.8 Roles & permissions — *BR-SYS-02*

Four new roles, replacing the current "System Manager only" grant on every doctype:

| Role | Full access | Read + write only | Read-only |
|---|---|---|---|
| Poultry Manager | Shed, Breed, Batch, Benchmark, all others | — | — |
| Poultry Attendant | Daily Log (create/write, no delete) | — | Shed, Breed, Batch |
| Vaccination In-charge | Vaccination Record, Vaccination Due (status only) | — | Batch, Breed |
| Feed Mill Operator | Feed Formula, Feed Production | — | Batch (to see feed warehouse) |

`System Manager` keeps full access to everything as the administrative fallback, per Frappe convention.

## 3. Daily Register Parity (new, 2026-09-28)

Sourced from a real customer's paper daily register (BRD §3.3). Closes `BR-FLK-12`, `BR-EGG-03`, `BR-FED-06` through `BR-FED-08`, `BR-EXP-01`, `BR-SALES-01`/`02`, `BR-SYS-03`.

### 3.1 Per-day mortality % on Poultry Daily Log — *BR-FLK-12*

Add read-only field `daily_mortality_pct` (Percent). Computed in `validate()`, alongside the existing `compute_mortality_rollup()`: `mortality_count &divide; batch.current_bird_count &times; 100` (the batch's count as it stands before this log submits — the same "safe at zero" guard already used for `hdep_percent` applies here: `0` when `current_bird_count` is `0`, not a divide-by-zero error).

### 3.2 Double Yolk grade + tray counts — *BR-EGG-01 (amended), BR-EGG-03*

Add `Double Yolk` to `Poultry Daily Log Egg Entry.grade`'s Select options (`Hatching Egg\nTable Egg\nJumbo Egg\nCracked Egg\nWaste Egg\nDouble Yolk`).

Add a new Single doctype **Poultry Settings** (global config, one record) with `eggs_per_tray` (Int, default `30`) — farms pack differently, so this is configurable, not hardcoded.

Add read-only field `trays` (Float) to `Poultry Daily Log Egg Entry`, computed in the same `compute_egg_rollup()` pass as `closing_count`: `production_count &divide; eggs_per_tray` (fetched once from `Poultry Settings` per save, not per row).

### 3.3 Feed logged in an alternate unit — *BR-FED-06*

Add two fields to `Poultry Daily Log`: `feed_uom` (Link &rarr; UOM, optional) and `feed_qty` (Float, optional — the quantity entered in `feed_uom`). `feed_consumed_kg` stays the canonical field everything else (Stock Entry, FCR, reports) already reads.

Business rule in `create_feed_stock_entry()` (or a new `apply_feed_uom_conversion()` called from `validate()` before it): if `feed_uom` and `feed_qty` are both set, compute `feed_consumed_kg = feed_qty &times; conversion_factor`, where the conversion factor comes from ERPNext's own `erpnext.stock.get_item_details.get_conversion_factor(feed_item, feed_uom)` — reusing ERPNext's existing Item UOM Conversion Detail table rather than inventing a bag-size field ourselves (per this app's own "use standard APIs before adding custom logic" rule). If `feed_uom` is left blank, behavior is unchanged: `feed_consumed_kg` is entered directly, exactly as today — fully backward compatible with every existing Daily Log.

### 3.4 Feed cost per batch/date — *BR-FED-07* (report, no schema change)

`Poultry Daily Log.stock_entry` already links to a real, valued ERPNext Stock Entry. Extend the **Poultry Feed Consumption Report** (already built) to join `Stock Entry Detail` on that link and pull its `amount` (ERPNext's own FIFO/valuation-computed cost) alongside `feed_consumed_kg` — no new field anywhere, this is purely a report-side join onto data ERPNext already has.

### 3.5 Production cost per egg — *BR-FED-08* (report, no schema change)

New report **Poultry Egg Production Cost**: per batch and date range, sum feed cost (§3.4's join) &divide; sum `total_eggs_produced` (already on `Poultry Daily Log`). Depends only on §3.4 existing.

### 3.6 Daily expenses — *BR-EXP-01*

New child doctype **Poultry Daily Log Expense** (`istable: 1`, no permissions block): `description` (Data, required), `amount` (Currency, required).

Add `expenses` (Table &rarr; Poultry Daily Log Expense) and a read-only rollup `total_expenses` (Currency, summed in `validate()`) to `Poultry Daily Log`.

### 3.7 Egg sales — *BR-SALES-01, BR-SALES-02*

New doctype **Poultry Egg Sale** — submittable, autoname `format:PES-{YYYY}-{#####}`:

| Field | Type | Rule |
|---|---|---|
| `batch` | Link &rarr; Poultry Batch, required | |
| `customer` | Link &rarr; Customer, required | reuses ERPNext's own Customer master rather than a new Poultry-specific buyer list |
| `sale_date` | Date, required, default Today | |
| `items` | Table &rarr; Poultry Egg Sale Item, required | |
| `total_amount` | Currency, read-only | summed from `items` |

**Poultry Egg Sale Item** (child, `istable: 1`): `grade` (Select, same options as `Poultry Daily Log Egg Entry.grade`, required), `quantity` (Int, required), `rate` (Currency, required), `amount` (Currency, read-only, `quantity &times; rate`).

Validation on submit, per grade row: compute cumulative production for that batch+grade up to `sale_date` (same query shape as `get_previous_closing()` on `Poultry Daily Log`) minus cumulative already-sold quantity for that batch+grade up to `sale_date` from other submitted `Poultry Egg Sale` rows; reject if this sale's `quantity` would exceed that available balance — mirrors `Poultry Chick Transfer.validate_against_hatch()`'s cap-checking pattern exactly.

**Design note on BR-SALES-02 ("reduces the egg stock ledger"):** `Poultry Egg Sale` does **not** mutate `Poultry Daily Log Egg Entry` rows — those stay a pure production ledger, submittable and immutable once submitted, exactly as already built and tested. Instead, "current egg stock" becomes a **report-time computation**: cumulative production (from Egg Entry) minus cumulative sales (from Egg Sale) per batch and grade. This avoids retroactively touching submitted, immutable Daily Log documents to reflect a later sale, and keeps one clear owner per concern (Daily Log owns production, Egg Sale owns sales, a report nets them) rather than two doctypes both claiming ownership of "closing stock."

### 3.8 Shed default feed warehouse — *BR-SYS-03*

Add `default_feed_warehouse` (Link &rarr; Warehouse) to `Poultry Shed`. In `Poultry Batch.validate()`, when the batch is new and `feed_warehouse` is blank, default it from `shed.default_feed_warehouse` if set — explicit controller logic (`if not self.feed_warehouse: self.feed_warehouse = frappe.db.get_value(...)`), not a `fetch_from`, so a user who deliberately picks a different warehouse for one batch is never silently overridden. Once every shed has a default warehouse, a genuine per-shed feed stock ledger (BRD §3.3's original ask) is just ERPNext's own Stock Ledger report filtered to that warehouse — nothing new to build there.

## 4. Traceability

Every `BR-*` in the BRD maps to exactly one row above (as-built §1, proposed-and-now-built §2, or newly-proposed §3), with the sole exception of `BR-SYS-01`, which is a structural constraint satisfied by the whole document rather than one field (no doctype anywhere introduces a parallel Item/stock/BOM model).
