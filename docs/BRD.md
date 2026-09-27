# Business Requirements Document — Poultry Module

**App:** `ob_poultry` &middot; **Module:** Poultry &middot; **Status:** Draft v1 &middot; **Owner:** Farm Operations

## 1. Purpose

Define the business requirements for a poultry flock-management and feed-manufacturing module built on Frappe/ERPNext, so the business can run day-to-day farm operations (bird batches, daily readings, vaccination, feed production) inside the same system it already uses for stock and accounting, instead of a separate spreadsheet or third-party tool.

## 2. Background

The business raises poultry (broiler/layer/breeder flocks) across one or more sheds and mills its own feed on-site. Today this is tracked outside the ERP. A reference poultry ERP already in production use (see [Poultry ERP Field Map](https://claude.ai/artifact/3zkz35pEzLyfjnauUHjZ2N)) was reviewed to ground these requirements in what a working poultry operation actually tracks day to day, rather than guessing at the domain.

## 3. Scope

### 3.1 In scope (v1)

- Shed and breed master data.
- Flock/batch lifecycle: placement, daily readings (mortality, feed, water, body weight, eggs), closure.
- Cause-coded mortality and graded egg production.
- Feed formulas (recipes) and feed production runs, built on ERPNext's own Item/BOM/Work Order/Stock Entry engine.
- Vaccination scheduling and administration.
- Batch performance metrics (FCR, CFCR, HDEP) benchmarked against breed/age standards.
- Role-scoped permissions for farm staff.

### 3.2 Out of scope (v1) — explicitly deferred

- **Contract farming** (external farmers raising birds under contract, growing-charge payment schemes, branch/line farmer routing). Real-world reference shows this is a large, separate domain (Placement, Farmer, Scheme, Rate Matrix) — not needed until the business actually contracts out growing.
- **Hatchery equipment stages** (Setter/Hatcher/Pullout, egg allotment from own vs. purchased sources). Only relevant once the business runs its own incubation.
- **Sales, purchase, HR, and accounting workflows** — these are already covered by ERPNext's own Selling, Buying, HR, and Accounts modules; the Poultry module integrates with them (e.g. feed stock) rather than re-implementing them.
- **Dashboards/report library** — deferred to a later pass once the underlying data (FCR, benchmarks, cause-coded mortality) actually exists to report on.

### 3.3 In scope (v3 — Daily Register Parity)

Sourced directly from a real customer's paper daily register (a per-shed layer/breeder log covering egg grading, feed, mortality, cost, and sales), photographed and reviewed 2026-09-28. Everything below is something the business already tracks by hand today, not a hypothetical feature:

- Daily mortality/loss % per batch (we track cumulative; the register shows it daily, per shed).
- Double-yolk eggs as a distinct, trackable egg grade.
- Egg counts expressed in trays (eggs are physically stored and counted in trays on the farm floor), not just raw counts.
- Feed logged in the unit the floor actually uses (bags), converted to kg via standard quantity conversion rather than requiring kg entry by hand.
- Feed cost/valuation surfaced per batch and date, sourced from ERPNext's own stock valuation rather than manually entered.
- Production cost per egg (feed cost &divide; eggs produced), a number the register computes by hand today.
- Ad hoc daily expenses per batch (the register has a dedicated "EXPENCES" line per shed).
- An egg sales ledger — buyer, quantity, rate — since the register's "SALES" block is literally a sales register, not just a production log.

## 4. Stakeholders / user roles

| Role | Responsibility |
|---|---|
| Farm Manager | Owns sheds and batches; approves batch closure; reviews performance vs. benchmark |
| Farm Attendant | Enters daily readings (mortality, feed, water, weight, eggs) |
| Vaccination In-charge | Administers and records vaccinations against the due schedule |
| Feed Mill Operator | Defines feed formulas; runs feed production |
| System Manager | Administers masters (sheds, breeds, benchmarks, vaccination templates) and permissions |

## 5. Business processes

### 5.1 Flock lifecycle

Shed prepared → batch placed (breed, initial bird count, start date) → daily readings recorded until closure → batch closed with an end date. Bird count is always a derived fact (initial count minus recorded mortality/culls), never a number typed in directly, so it can't drift out of sync with the daily record.

### 5.2 Vaccination lifecycle

A breed carries a standard vaccination schedule (vaccine + dose + method, keyed by bird age in days). Placing a batch instantiates a due-list from that schedule. The Vaccination In-charge records actual administration against each due item.

### 5.3 Feed manufacturing lifecycle

Feed Mill Operator defines a formula (raw materials + medicine/additive ingredients, with quantities and percentages) for a finished feed item → generates a Bill of Materials from it → produces the feed in configurable batch multiples via a Work Order → actual output is recorded and checked against the theoretical target (yield %).

## 6. Business requirements

Numbered for traceability into the FIT-GAP analysis and FRD. `Shall` requirements are mandatory for v1 sign-off; `should` requirements are desirable but may slip to v1.1.

### Flock & batch management (BR-FLK)

- **BR-FLK-01** — The system shall record poultry housing units (sheds), each with a bird capacity.
- **BR-FLK-02** — The system shall maintain a breed master, classified by type (Broiler / Layer / Breeder / Dual Purpose), carrying a standard FCR.
- **BR-FLK-03** — The system shall track a batch (flock) from placement, recording shed, breed, start date, and initial bird count, and shall reject a batch whose initial bird count exceeds its shed's capacity.
- **BR-FLK-04** — The system shall maintain each batch's current bird count as a value derived from its daily records, not as an independently editable field.
- **BR-FLK-05** — The system shall record daily mortality and culls per batch, and shall reject any entry that would make cumulative removals exceed the batch's initial bird count.
- **BR-FLK-06** — The system should record mortality by cause (disease, injury, heat stress, other) and by sex, not only as a single count.
- **BR-FLK-07** — The system shall record daily feed consumption per batch and automatically deplete the corresponding feed item's stock in the batch's assigned warehouse.
- **BR-FLK-08** — The system shall record daily average body weight and water consumption per batch.
- **BR-FLK-09** — The system should compute Feed Conversion Ratio (FCR) and mortality-corrected FCR (CFCR) per batch from cumulative feed consumption and body weight.
- **BR-FLK-10** — The system should maintain breed/age-specific standard benchmarks (mortality %, feed per bird, body weight, FCR) and show actuals against them.
- **BR-FLK-11** — The system shall allow closing a batch with an end date and shall reject further daily entries against a closed batch.
- **BR-FLK-12** — The system should compute a per-day mortality/loss % per batch (today's mortality &divide; current bird count), not only the cumulative batch-level mortality %.

### Egg production (BR-EGG)

- **BR-EGG-01** — The system should record daily egg production per batch broken down by grade (Hatching / Table / Jumbo / Cracked / Waste / Double Yolk), each with an opening count, production count, closing count, and average egg weight.
- **BR-EGG-02** — The system should compute Hen-Day Egg Production % (HDEP) automatically from daily egg records and current bird count.
- **BR-EGG-03** — The system should record a tray count alongside the raw egg count per grade, using a configurable eggs-per-tray conversion.

### Vaccination (BR-VAC)

- **BR-VAC-01** — The system should maintain a vaccination schedule template per breed, keyed by bird age in days, each item naming a vaccine, dose, and administration method.
- **BR-VAC-02** — The system should generate a per-batch vaccination due-list from the breed's template at the time of placement.
- **BR-VAC-03** — The system shall record vaccination administration (vaccine, dose, method, date given, administered by, next due date) per batch, and shall reject a next-due-date earlier than the date given.

### Feed manufacturing (BR-FED)

- **BR-FED-01** — The system shall maintain a feed formula per finished feed product, listing ingredients with quantities and a computed percentage of batch size.
- **BR-FED-02** — The system should distinguish bulk raw-material ingredients from micro/medicine (additive) ingredients within a formula.
- **BR-FED-03** — The system shall generate a manufacturing Bill of Materials from a feed formula and allow producing it in configurable batch multiples via a Work Order.
- **BR-FED-04** — The system should record actual production output and compute a yield % against the theoretical target (formula quantity &times; batch multiple).
- **BR-FED-05** — The system should surface feed production cost per kg from ingredient valuation.
- **BR-FED-06** — The system should allow daily feed consumption to be entered in an alternate unit (e.g. bags) and converted to the feed item's stock unit automatically, rather than requiring the kg figure to be calculated by hand.
- **BR-FED-07** — The system should surface the actual cost (valuation) of feed consumed per batch and date, sourced from ERPNext's stock valuation rather than a manually entered rate.
- **BR-FED-08** — The system should compute production cost per egg (feed cost &divide; eggs produced) per batch and date range.

### Expenses (BR-EXP)

- **BR-EXP-01** — The system should allow ad hoc daily expenses to be recorded against a batch, each with a description and amount.

### Egg sales (BR-SALES)

- **BR-SALES-01** — The system should record an egg sale against a customer, itemized by grade, quantity, and rate, with a computed total amount.
- **BR-SALES-02** — The system should reduce a batch's egg stock ledger (per-grade closing balance) by quantities sold, so closing stock always reconciles against production minus sales minus damage.

### System (BR-SYS)

- **BR-SYS-01** — The system shall integrate with ERPNext's existing Item, BOM, Work Order, and Stock Entry doctypes for inventory and manufacturing rather than duplicating that logic.
- **BR-SYS-02** — The system should restrict data entry and approval actions by role, distinguishing at minimum Farm Manager, Farm Attendant, Vaccination In-charge, and Feed Mill Operator.
- **BR-SYS-03** — The system should let a shed carry a default feed warehouse, so batches placed in it don't require re-entering the same warehouse each time, and so a per-shed feed stock ledger is possible via ERPNext's own Stock Ledger report.

## 7. Assumptions & constraints

- ERPNext's Setup Wizard (Company, Chart of Accounts, Item Group, UOM, Warehouse) is completed before any feed-manufacturing or stock-consumption feature is used; this module does not perform that setup itself.
- One bird = one unit of count; sexed bird tracking (male/female counts, as the reference system does for breeder flocks) is not required for v1 broiler/layer batches and is deferred until breeder flocks are in scope.
- Benchmark curves (BR-FLK-10) are entered manually by a System Manager; no external breed-standard data feed is assumed.
- Eggs-per-tray (BR-EGG-03) is a configurable number, not a hardcoded 30 — different grades and operations pack differently.
- Egg sales (BR-SALES-01) record the transaction and its effect on egg stock; they do not themselves create an ERPNext Sales Invoice — that remains a manual step in Selling until there's a concrete need to automate it.

## 8. Success metrics

- A batch's current bird count, FCR, CFCR, and mortality % are always derivable from its daily records with no manual reconciliation step.
- Feed consumed by a batch is reflected in ERPNext stock within the same transaction that records the daily log, with no separate manual stock entry.
- A Feed Mill Operator can go from formula to a submitted Work Order in the Poultry module without opening ERPNext's Manufacturing workspace directly.
