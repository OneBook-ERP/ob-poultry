# Reports — Finalized List

Every report in poultry.care's own Reports menu (checked live at [erp.poultry.care/reports/report](https://erp.poultry.care/reports/report), 70 reports across 11 categories), triaged against our actual schema. Three outcomes per report:

- **Build now** — the data already exists in our doctypes; this is implementation, not design.
- **Needs schema** — real value, but needs a field or two we haven't built yet; noted what's missing.
- **Skip** — either it's a standard ERPNext report we already get for free (Sales/Purchase/Payables/Receivables/Accounts/HRMS/Taxes — per BRD §3.2, out of scope by design), or it depends on a roadmap item we've deliberately not built (field-visit logging, settlement vouchers with TCS/TDS, hatchery equipment sub-stages).

All "Build now" reports should be built as Frappe **Query Reports** (Script Report type, module "Poultry") rather than custom pages — that gets filters, export, and charting for free from Frappe's own report UI, instead of rebuilding poultry.care's bespoke report pages.

## CBF (22 reports)

| Report | Verdict | Notes |
|---|---|---|
| Mortality | **Build now** | Cross-batch rollup by date range/branch/line/farmer, using `mortality_details`. We have cause codes theirs doesn't show in this view — ours can be strictly better here. |
| Batch Analysis | **Build now (lean)** | P&L per placement: opening/mortality/closing birds, feed consumption, growing charge. Their version also nets Chick Cost/Med Cost/Admin Cost/Sales Amount — we don't have Purchase/Sales cost attribution wired to a batch yet, so ours omits those columns rather than faking them. |
| Growing Charges | **Build now (lean)** | List contract batches with their computed `growing_charge_amount`. Their version is a full settlement voucher with TCS/TDS withholding and manual adjustment lines — that's the "Settlement transparency reporting" v3+ roadmap item, not this report. |
| Medication | **Build now** | `Poultry Vaccination Record` list across batches, filterable by date/batch/vaccine. |
| Active Farms / Live Farms | **Build now** | `Poultry Batch` filtered `status=Active`, `flock_source=Contract`. (Two names for the same thing in their system.) |
| Empty Farms | **Build now** | `Poultry Shed` with no `Poultry Batch` currently `Active` against it. |
| Farmer Balances | **Needs schema** | Needs Accounts Receivable/Payable wired to `Poultry Farmer` — ERPNext already does this for any Party once a Farmer is linked as one; not yet done. |
| Birds Placement / Chicks Placement | **Build now** | `Poultry Batch` list by placement date range. (Same report, two names in their menu.) |
| Farmers | **Build now** | Trivial `Poultry Farmer` list/directory. |
| Matured Birds | **Build now** | Batches where `age >= threshold` (age derived the same way `Poultry Daily Log.apply_benchmarks()` already computes it). |
| Farm Stock Cost | **Needs schema (now scoped)** | Needs feed cost attributed per farm/warehouse — closed by ROADMAP.md's Daily Register Parity Epic 18 (shed default feed warehouse); once every shed has one, this is ERPNext's own Stock Ledger report filtered by warehouse, not a custom build. |
| Lifting (Batchout) / Lifting (Pending) / Birds Sales Summary / Birds Sales With Date | **Needs schema** | All depend on a *bird*-sale transaction linked to a batch — still not modeled. Note this is distinct from the *egg* sales ledger now scoped as Epic 17 (Daily Register Parity); egg sales and bird sales are separate gaps that happen to sound similar. |
| Inter Farm Feed Transfer | **Needs schema** | ERPNext's own Stock Entry (Material Transfer) already does the mechanics; needs each farm to have its own Warehouse before this is meaningful. |
| Month Wise Cost Report | **Needs schema** | Same gap as Farm Stock Cost, aggregated monthly. |
| Lineruns / Unvisited Farms | **Skip** | Field-officer visit logging — explicitly v3+ (GPS-verified field visits), not built. |

## Hatchery (9 reports)

| Report | Verdict | Notes |
|---|---|---|
| Chick Transfers | **Build now** | `Poultry Chick Transfer` list, trivial. |
| Chick Summary | **Build now** | `Poultry Hatch.actual_chicks` rolled up by hatchery/date range. |
| Chick Stock | **Build now** | Per hatch: `actual_chicks - sum(submitted Poultry Chick Transfer quantities)` — the same arithmetic `Poultry Chick Transfer.validate_against_hatch()` already does inline, just surfaced as a report instead of a validation check. |
| Hatches Performance | **Needs schema** | Their version compares actual vs. standard egg weight and chick weight per hatch. `Poultry Hatch` only has `eggs_set`/`standard_hatchability_pct`/`actual_chicks` today — would need `egg_weight_g`, `chick_weight_g`, and their standards added first. |
| Economy Report | **Needs schema** | Needs egg cost data (own vs. purchased egg valuation) we don't track — out of scope per ROADMAP.md's "own-vs-purchased egg sourcing split," deliberately not built. |
| Egg Stock By Transaction | **Needs schema** | Needs egg treated as trackable inventory with a transaction ledger — we track egg *production* (`Poultry Daily Log Egg Entry`) but not egg *stock* as a distinct inventory concept. |
| Setting / Candling / Transfer | **Skip** | Separate Setter/Hatcher/Pullout equipment sub-stage tracking — explicitly deferred in ROADMAP.md's lean Hatchery slice. |

## Feed Mill (8 reports)

| Report | Verdict | Notes |
|---|---|---|
| Production | **Build now** | `Poultry Feed Production` list. |
| Production by Feed | **Build now** | Group `Poultry Feed Production` by `formula.feed_item`. |
| Production by Formula | **Build now** | Group by `formula`. |
| Production Sheet | **Build now** | Per-production printable summary — we already have the data (formula ingredients &times; batch count), just needs a Report wrapper instead of only a doc view. |
| Compare Formula | **Build now** | Pivot: raw materials as rows, formulas as columns, quantities as cells — direct match to `Poultry Feed Formula` + `Poultry Feed Formula Ingredient`. Genuinely useful once more than 2-3 formulas exist. |
| Feed Demand | **Needs schema** | Real forecasting logic (project feed need from batch age curves against `Poultry Benchmark.standard_feed_per_bird_g`) — doable, but it's a small algorithm, not a data pull; scope as its own task. |
| Production by Formula Stock | **Needs schema** | Needs stock valuation tied to formula, beyond what `Poultry Feed Production.cost_per_kg` (currently unset, per FRD §2.7) provides yet. |
| Feed Mill Stock | **Skip** | ERPNext's own Stock Balance report, filtered to feed items, already covers this. |

## Breeder (9 reports)

| Report | Verdict | Notes |
|---|---|---|
| Medication | **Build now** | Same report as CBF's Medication, just also usable for Breeder-type batches. |
| Egg Collection | **Build now** | Daily/period egg production by grade, from `Poultry Daily Log Egg Entry` — we have this data in more structured form (grade-level opening/closing ledger) than most of their view shows. |
| Feed | **Build now** | Feed consumption per batch/period from `Poultry Daily Log.feed_consumed_kg`. |
| Bodyweight Report | **Build now** | `average_body_weight_g` trend per batch over time, plotted against `Poultry Benchmark.standard_body_weight_g`. |
| Batch Performance Review | **Build now** | Mortality/feed/weight/FCR/CFCR trend per batch — this is largely what `Poultry Batch`'s own derived fields plus the Daily Log ledger already provide; the report is a multi-batch comparison view over them. |
| Birds | **Build now** | Bird count (and, for breeder flocks, the `male_bird_count`/`female_bird_count` split) over time per batch. |
| Performance* | **Needs schema** | Their weekly hen-housed %, HE/HH%, depletion-curve report needs sexed *daily* tracking (feed/mortality split by sex per day) — explicitly flagged in ROADMAP.md as the top "v2 depth" follow-up, not yet built. A simpler weekly HDEP rollup (using what we already have) could ship first as a lighter substitute. |
| Birds Sales / Lifting (Batchout) | **Needs schema** | Same bird-sale gap as the CBF equivalents. |

## Inventory (8 reports) — mostly skip, standard ERPNext

| Report | Verdict | Notes |
|---|---|---|
| Egg Transfer / Egg Stock | **Needs schema** | Same egg-as-inventory gap noted under Hatchery. |
| Inventory Summary, Detailed Stock, Feed Transfer (Goods), Issued Items, Feed Stock | **Skip** | ERPNext's own Stock Balance / Stock Ledger / Stock Entry list reports already cover these exactly — our Daily Log and Feed Production already post through standard Stock Entries, so these reports work today with zero extra code, just point at ERPNext's existing reports. |

## Sales, Receivables, Purchase, Payables, Accounts, HRMS, Taxes (27 reports) — all skip

Every report in these seven categories is a standard business report (sales/purchase registers, aging, ledgers, employee/attendance, GST/TDS) that ERPNext already provides once the corresponding module (Selling, Buying, Accounts, HR) is actually used. Per BRD §3.2, we deliberately don't duplicate these — building a parallel report here would mean maintaining two sources of truth for the same numbers ERPNext already reports correctly.

## Finalized build list, in priority order

**Batch 1 — pure data pulls, no new fields needed (build these first):**
1. Mortality (cross-batch)
2. Batch Analysis (lean)
3. Growing Charges (lean)
4. Medication
5. Active/Live Batches, Empty Sheds
6. Birds Placement
7. Farmers directory
8. Chick Transfers, Chick Summary, Chick Stock
9. Production, Production by Feed, Production by Formula, Production Sheet
10. Compare Formula
11. Egg Collection, Feed (consumption), Bodyweight, Batch Performance Review, Birds (count/sexed)

**Batch 2 — needs a small schema addition first, each independently scoped:**
- Feed Demand (needs a forecasting method, not new fields)
- Hatches Performance (needs `egg_weight_g`/`chick_weight_g` + standards on `Poultry Hatch`)
- Weekly breeder Performance rollup, lighter substitute for the full sexed-daily version

**Not building:** bird-sale-dependent reports (Lifting/Birds Sales, both modules) until a bird-sale transaction exists; settlement-voucher Growing Charges (TCS/TDS) until that's actually needed; field-visit reports (Lineruns/Unvisited Farms); egg-as-inventory reports (Egg Stock/Transfer/Economy Report); hatchery equipment sub-stage reports (Setting/Candling/Transfer); all 27 standard-ERPNext-covered reports.

## Daily Register Parity reports (new, Epics 14/15/17)

Not in poultry.care's own catalog — surfaced directly from a customer's paper register (BRD §3.3), not benchmarked against the reference ERP:

| Report | What it answers | Epic |
|---|---|---|
| Poultry Feed Consumption Report (extended) | Feed cost per batch/date, pulled from the Stock Entry's own ERPNext valuation | 14 |
| Poultry Egg Production Cost | Cost per egg produced (feed cost &divide; eggs produced) per batch/date range | 15 |
| Poultry Net Egg Stock (new) | True closing egg stock per batch/grade — production minus sales, not just production | 17 |

These three complete the paper register's "Production Cost 4.19/4.17" and "SALES" blocks, which had no equivalent anywhere in either the original Batch 1 list or the reference ERP's own catalog for this exact shape.
