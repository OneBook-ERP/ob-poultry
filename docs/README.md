# Poultry Module Documentation

Reading order for the Poultry module of `ob_poultry`:

1. [BRD.md](./BRD.md) — Business Requirements Document. Why the module exists, who uses it, and what the business needs it to do, numbered as traceable `BR-*` requirements.
2. [FIT_GAP_ANALYSIS.md](./FIT_GAP_ANALYSIS.md) — maps every `BR-*` requirement against the doctypes and logic that already exist in this app, and marks each one Fit, Partial, or Gap.
3. [FRD.md](./FRD.md) — Functional Requirements Document. Doctype-level spec (fields, validations, business rules, formulas) for what is already built and for what closes the gaps, each item traceable back to a `BR-*`.
4. [TASKS_AND_TEST_CASES.md](./TASKS_AND_TEST_CASES.md) — the FRD broken into epics and tasks, each with test cases and pass/fail success criteria.
5. [ROADMAP.md](./ROADMAP.md) — where the module is now, what's next, and what's been considered and deliberately deferred (including features found in neither our app nor the reference ERP).

Source material: [Poultry ERP Field Map](https://claude.ai/artifact/3zkz35pEzLyfjnauUHjZ2N), a read-only survey of a live production poultry ERP, used to sanity-check what a real operation needs beyond a first working version.

Scope note: this documents the **Poultry** module only (sheds, breeds, batches, daily logs, vaccination, feed formulas). It does not cover contract farming, hatchery, or the rest of `ob_poultry`'s eventual scope — those are out of scope here and called out as such in the BRD.
