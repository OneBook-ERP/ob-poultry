# Roadmap — Poultry Module

Where the module is, what closes the known gaps next, and what's been considered and deliberately deferred. Phases are priority order, not committed dates.

## Now — shipped

**v1 core** (FRD §1): Shed/breed masters, batch placement with capacity check, derived bird count from a daily-log ledger, feed consumption posting Stock Entries against ERPNext stock, ad hoc vaccination records, and feed formula &rarr; BOM &rarr; Work Order.

**v1.1 gap closure** (FRD §2 / TASKS_AND_TEST_CASES.md Epics 1&ndash;9), all nine implemented and verified (41/41 test scenarios): cause-coded mortality, graded egg production + HDEP, standard breed/age benchmarks, FCR/CFCR, vaccination scheduling from a breed template, feed formula ingredient categories, feed production yield %, roles and scoped permissions, closed-batch guard.

**v2, lean slice** &mdash; the deferred items below, built deliberately smaller than the reference ERP's versions (extending what exists rather than duplicating a parallel module stack), verified (15/15 test scenarios):

- **Contract farming**, as an extension of `Poultry Batch` rather than a separate CBF stack: `Poultry Farmer` (master), `Poultry Growing Charge Scheme` + `Poultry Growing Charge Rate` (weight-bracket rate table &mdash; this **is** the lean version of "Rate Matrix" below, folded in rather than built as its own generic 4-doctype pricing engine), `Poultry Batch.flock_source` (Owned/Contract) with `farmer`/`growing_charge_scheme` fields and a `calculate_growing_charge()` method. Contract batches reuse the existing Daily Log, vaccination, and FCR machinery as-is &mdash; no parallel Day Entry/Placement doctypes. **Not built**: Branch/Line field-officer routing beyond two free-text fields on Farmer, farmer performance history rollups, Multi Inward/Feed Transfer/Bird Adjustment transaction types.
- **Hatchery**, as three focused doctypes: `Poultry Hatchery` (master), `Poultry Hatch` (schedule/setting/candling/transfer/hatch dates, hatchability % &rarr; estimated chicks), `Poultry Chick Transfer` (submittable, validates against the hatch's actual chick count). **Not built**: separate Setter/Hatcher/Pullout equipment-level sub-records, own-vs-purchased egg sourcing split.
- **Sexed bird tracking**: `male_bird_count`/`female_bird_count` summary fields on `Poultry Batch`. **Not built**: sexed daily feed/mortality entry (the reference ERP splits the whole Day Entry form by sex for breeder flocks) &mdash; this stays a batch-level summary, not a daily-level breakdown, until a real breeder-flock user needs it.
- **Item-level nutrient composition**: `nutrients` child table on `Poultry Feed Formula` (nutrient/value/unit, free entry) rather than on ERPNext's core `Item` doctype, so it needed no Custom Field on a standard doctype.
- **Mortality photo attachments**: `photo` (Attach Image) field on `Poultry Daily Log Mortality Entry`.

**Rate Matrix**, as noted above, is done &mdash; folded into Growing Charge Scheme rather than built as a standalone generic pricing engine, since the only consumer of it in this app is growing-charge calculation.

**Daily Register Parity, shipped** (from real customer evidence): a real customer's paper daily register (photographed and reviewed 2026-09-28) surfaced eight concrete gaps &mdash; not inferred, directly observed in what the business already tracks by hand. Scoped in [BRD.md](./BRD.md) &sect;3.3, designed in [FRD.md](./FRD.md) &sect;3, built and verified (21/21 integration tests) as [TASKS_AND_TEST_CASES.md](./TASKS_AND_TEST_CASES.md) Epics 11&ndash;19:

1. Per-day mortality % per batch (Epic 11).
2. Double Yolk and Dirty Egg egg grades + tray counts, via a new `Poultry Settings` singleton holding a configurable `eggs_per_tray` (Epic 12).
3. Feed logged in bags, converted to kg via ERPNext's own UOM conversion (Epic 13) &mdash; reuses ERPNext's existing conversion-factor API rather than inventing a bag-size field; blank `feed_uom` keeps direct-kg entry working exactly as before.
4. Feed cost per batch/date, sourced from ERPNext's own stock valuation (Epic 14, report-only: `Poultry Feed Consumption Report` extended with a `Stock Entry Detail` join).
5. Production cost per egg (Epic 15, new `Poultry Egg Production Cost` report).
6. Ad hoc daily expenses per batch, via new child doctype `Poultry Daily Log Expense` (Epic 16).
7. An egg sales ledger &mdash; buyer, quantity, rate &mdash; via new submittable doctype `Poultry Egg Sale` + `Poultry Egg Sale Item`, capped against a report-time net-stock computation (`Poultry Net Egg Stock`) rather than mutating the immutable production ledger (Epic 17).
8. Shed default feed warehouse (Epic 18) &mdash; closes the "Farm Stock Cost" gap via ERPNext's own Stock Ledger report, nothing custom needed.

Plus, folded in from a second image of the customer's own "Data Entry"/"dashboard" field list (Epic 19): `feed_per_bird_g` and `damage_pct` computed fields on `Poultry Daily Log`, and four farm-wide "Today" Number Cards (Eggs Produced, Feed Consumed Kg, Mortality, Culled) on the Poultry workspace. Ratio/per-batch metrics from that same list (age in weeks, tray stock) were deliberately left on records/reports rather than forced into single farm-wide Number Cards &mdash; they don't reduce to one number across every active batch.

## Next — v2 depth (not yet built, real gaps in what shipped above)

Concrete follow-ups on the lean v2 slice, roughly in the order they'd bite:

1. Sexed *daily* tracking (feed/mortality by sex, not just a batch-level count) &mdash; needed once actual breeder flocks are managed day-to-day, not just placed.
2. Farmer performance history (previous-batch FCR/CFCR/mortality% surfaced when placing a new contract batch) &mdash; the reference ERP does this automatically; we don't yet.
3. `Poultry Feed Production.cost_per_kg` &mdash; still intentionally left unset (see FRD §2.7); wire it once a completed Work Order's actual costing is worth surfacing here instead of in ERPNext's own reports.
4. Growing charge settlement transparency &mdash; show the farmer the exact bracket/rate/weight math behind `growing_charge_amount`, not just the final number.

## Exploratory — v3+, not in either system today

Surfaced by researching what modern poultry farm software offers beyond flock/feed/mortality tracking (neither our app nor the reference ERP has these, at least not visibly):

- **Offline-first mobile capture for shed workers.** Ranked highest of this group &mdash; daily logs are entered in sheds with poor connectivity in practice, so a sync-when-reconnected mobile flow is closer to a real operational need than a nice-to-have, once this leaves pilot stage.
- **IoT environmental monitoring** &mdash; shed temperature/humidity/ammonia with threshold alerts, ideally driving fan/heater control loops. **Before building this: check whether poultry.care's own IoT/silo-sensor features are already licensed on the tenant we reviewed** &mdash; their marketing site advertises this, so it may be a licensing question rather than a feature gap.
- **Feed-silo and water-tank level sensors** feeding low-stock alerts into inventory directly, same licensing caveat as above.
- **Biosecurity / visitor log** with geofencing &mdash; who entered which shed and when, relevant for disease containment.
- **GPS-verified field visits** for vets or field officers doing rounds.
- **Predictive mortality and average-weight modeling** a few days out from feed/water/temperature trends.
- **Anomaly detection** on daily readings to flag disease onset before it shows up in raw mortality numbers.
- **Breeding pair/trio lineage tracking** &mdash; only relevant once a genetics/breeding program, not just flock management, is in scope.

## Working rule

A v3+ item graduates to v2, and a v2-depth item graduates to shipped, only when a real operational need forces it &mdash; not by default ordering. Check this file before assuming something is missing; it may already be here, deliberately not yet built.
