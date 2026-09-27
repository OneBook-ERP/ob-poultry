# OB Poultry

A Frappe app for running a poultry operation end to end: flock lifecycle (sheds, breeds, batches, daily readings), vaccination scheduling, feed formulation and production, contract farming, and hatchery — built on top of ERPNext's own stock, manufacturing, and accounting rather than duplicating them.

## What's in the Poultry module

**Flock management**
Sheds and breeds are masters. A `Poultry Batch` is one flock — owned or placed with a contract farmer — tracked from placement to closure. Daily readings (`Poultry Daily Log`) capture cause-coded mortality, feed consumption (which posts a real Stock Entry against ERPNext inventory), body weight, and graded egg production. A batch's bird count, cumulative feed, FCR, and CFCR are always derived from its submitted daily logs — never hand-edited — so they can't drift out of sync with the record.

**Vaccination**
A `Poultry Vaccination Schedule Template`, keyed by bird age, generates a `Poultry Vaccination Due` list automatically when a batch of that breed is placed. `Poultry Vaccination Record` closes those out (or can be logged ad hoc).

**Feed Mill**
`Poultry Feed Formula` is a recipe — raw materials and medicine/additive ingredients, categorized, with a computed percentage of batch size and optional nutrient values — that generates a real ERPNext BOM. `Poultry Feed Production` wraps a Work Order run against that BOM and tracks planned vs. actual yield.

**Contract farming**
A batch can be placed with a `Poultry Farmer` under a `Poultry Growing Charge Scheme` (weight-bracket payout rates) instead of being owned outright; `calculate_growing_charge()` computes the farmer's payout from the batch's current weight and bird count.

**Hatchery**
`Poultry Hatchery` and `Poultry Hatch` track incubation (eggs set, hatchability, actual chicks); `Poultry Chick Transfer` moves hatched chicks into a batch, validated against what the hatch actually produced.

**Reporting**
13 built-in Query Reports (Mortality, Batch Analysis, Growing Charges, Egg Production, Bodyweight, Feed Consumption, Compare Formula, Chick Stock, and more) live under the Poultry workspace's Reports section — see [docs/REPORTS.md](docs/REPORTS.md) for what each one shows and why it exists in that form.

**Roles**: `Poultry Manager` (full access), `Poultry Attendant` (daily logging only), `Vaccination In-charge` (vaccination records only), `Feed Mill Operator` (formulas and production only) — each scoped to just what that job needs, with `System Manager` as the administrative fallback.

## Documentation

Full requirements, design rationale, and test coverage live in [docs/](docs/):

- [docs/README.md](docs/README.md) — reading order for everything below
- [docs/BRD.md](docs/BRD.md) — why the module exists and what it needs to do, as numbered requirements
- [docs/FIT_GAP_ANALYSIS.md](docs/FIT_GAP_ANALYSIS.md) — those requirements checked against the actual code
- [docs/FRD.md](docs/FRD.md) — doctype-level functional spec
- [docs/TASKS_AND_TEST_CASES.md](docs/TASKS_AND_TEST_CASES.md) — build epics with pass/fail test cases
- [docs/ROADMAP.md](docs/ROADMAP.md) — what's shipped, what's next, what's deliberately deferred and why
- [docs/REPORTS.md](docs/REPORTS.md) — every report in the reference ERP we benchmarked against, triaged against this app's schema
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) — how to actually run a farm in this app, for Farm Managers, Attendants, Vaccination In-charges, and Feed Mill Operators

A regression test suite covering both the core module and its contract-farming/hatchery extensions lives at `ob_poultry/tests/test_poultry_module.py`.

## Prerequisites

This app builds on ERPNext's stock and manufacturing engine — complete ERPNext's own Setup Wizard (Company, Chart of Accounts, at least one Warehouse, a base Item Group and UOM) before using any feed-formula, feed-production, or feed-consumption feature. The Poultry module doesn't perform that setup itself.

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/OneBook-ERP/ob-poultry --branch develop
bench install-app ob_poultry
```

## Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/ob_poultry
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

Run the test suite with `bench --site your-site run-tests --app ob_poultry` against a dedicated test site (not a working/demo site — see the note in `ob_poultry/tests/test_poultry_module.py`).

## License

MIT
