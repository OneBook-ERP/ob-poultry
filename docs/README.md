# Poultry Module Documentation

**Using the app, not building it?** Start and stay at [USER_GUIDE.md](./USER_GUIDE.md) — day-to-day workflows for Farm Managers, Attendants, Vaccination In-charges, and Feed Mill Operators. Everything below this point is for people building or extending the module, not running a farm with it.

Reading order for the Poultry module of `ob_poultry`:

1. [BRD.md](./BRD.md) — Business Requirements Document. Why the module exists, who uses it, and what the business needs it to do, numbered as traceable `BR-*` requirements.
2. [FIT_GAP_ANALYSIS.md](./FIT_GAP_ANALYSIS.md) — maps every `BR-*` requirement against the doctypes and logic that already exist in this app, and marks each one Fit, Partial, or Gap.
3. [FRD.md](./FRD.md) — Functional Requirements Document. Doctype-level spec (fields, validations, business rules, formulas) for what is already built and for what closes the gaps, each item traceable back to a `BR-*`.
4. [TASKS_AND_TEST_CASES.md](./TASKS_AND_TEST_CASES.md) — the FRD broken into epics and tasks, each with test cases and pass/fail success criteria.
5. [ROADMAP.md](./ROADMAP.md) — where the module is now, what's next, and what's been considered and deliberately deferred (including features found in neither our app nor the reference ERP).
6. [REPORTS.md](./REPORTS.md) — every report in the reference ERP, triaged against our schema: build now, needs a schema addition first, or skip (already covered by ERPNext's standard modules).

Source material: [Poultry ERP Field Map](https://claude.ai/artifact/3zkz35pEzLyfjnauUHjZ2N), a read-only survey of a live production poultry ERP, used to sanity-check what a real operation needs beyond a first working version.

Scope note: this documents the **Poultry** module (sheds, breeds, batches, daily logs, vaccination, feed formulas, plus the lean v2 slice: contract farming, hatchery, growing charges — see ROADMAP.md for exactly what's in vs. deferred within each). It does not cover the rest of `ob_poultry`'s eventual scope beyond that.
