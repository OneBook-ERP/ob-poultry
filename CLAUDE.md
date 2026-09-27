# Agent Guide — ob_poultry

Custom Frappe/ERPNext app for poultry flock management and feed manufacturing. One module, `Poultry`, under `ob_poultry/ob_poultry/poultry/`. Built to run day-to-day farm operations (batches, daily readings, vaccination, feed production, egg sales) inside the same ERP the business already uses for stock and accounting, rather than a separate spreadsheet or third-party tool.

## Where the truth lives

Read `docs/` before making any non-trivial change — it is the source of truth for *why*, this file is only the source of truth for *how to work in the repo*. In order: `BRD.md` (numbered `BR-*` requirements) → `FIT_GAP_ANALYSIS.md` (Fit/Partial/Gap per BR against what's actually built) → `FRD.md` (doctype-level design, §1 as-built / §2 first gap-closure round / §3 latest round) → `TASKS_AND_TEST_CASES.md` (Epics, each with tasks + test cases, TC-IDs referenced as comments in the test file) → `ROADMAP.md` (phased priority, what shipped vs. what's deliberately deferred) → `REPORTS.md` (report-by-report build/skip triage against the reference ERP's own catalog) → `USER_GUIDE.md` (end-user docs — every claim in here was verified live in the browser before being written, not just read off the code). Keep these in sync when you change requirements or scope; a stale FIT_GAP_ANALYSIS.md or ROADMAP.md is worse than none, because it actively misleads the next session.

## Object model

`Poultry Batch` is the central entity — a flock from placement to closure. Its `current_bird_count`, `fcr`/`cfcr`, and mortality rollups are always *derived* from submitted `Poultry Daily Log` rows via `recalculate_performance()`, never hand-edited directly. This "one owner of state, derived not stored" rule applies throughout: egg opening/closing counts, HDEP%, damage%, feed-per-bird are all computed in `validate()`/`on_submit()`, not entered by a user. Don't break this pattern when adding fields — if a number can be computed from submitted child rows, compute it; don't add a parallel manually-editable field for the same fact.

Everything under `Poultry` reuses ERPNext's own Item/BOM/Work Order/Stock Entry/Customer rather than duplicating inventory, manufacturing, or party models. `Poultry Daily Log.create_feed_stock_entry()` posts a real Stock Entry; `Poultry Feed Formula` generates a real BOM and Work Order; `Poultry Egg Sale` reuses ERPNext's `Customer`. Before adding custom logic for something ERPNext already does (UOM conversion, stock valuation, stock ledgers), check whether the standard API already covers it — the feed-in-bags conversion (Epic 13) and feed-cost reports (Epics 14/15) are both built this way, reading ERPNext's own conversion factors and Stock Entry valuation rather than reinventing them.

## Commands

This bench is managed by the `pilot` CLI, not raw `bench`. From `/Users/kiddo_sha/pilot`:

- `pilot frappe --site poultary.localhost migrate` — sync doctype/JSON changes into the site. Run `clear-cache` first if a brand-new doctype module isn't picked up (Frappe caches the app's module list in Redis).
- `pilot build --apps ob_poultry` — compile client-side assets (`.js` client scripts, report filter files). Required after touching anything under a doctype's or report's `.js` file, or new UI buttons won't appear until this runs.
- `pilot frappe --site poultary.localhost run-tests --app ob_poultry` — run the integration test suite (`ob_poultry/tests/test_poultry_module.py`). If it complains tests are disabled, run `pilot frappe --site poultary.localhost set-config allow_tests true` once.
- `pilot frappe --site poultary.localhost execute <dotted.module.path.function>` — run a one-off script (module must define a callable at that path; auto-commits). Use `ob_poultry/patches/` for throwaway verification scripts and delete them when done — never leave one-off scripts in the app.
- `uvx ruff check ob_poultry` — lint. Config is tabs + double quotes (`pyproject.toml`'s `[tool.ruff.format]`), standard Frappe style.

## Testing discipline

`ob_poultry/tests/test_poultry_module.py` is one `IntegrationTestCase` class (`frappe.tests`, not the deprecated `frappe.tests.utils.FrappeTestCase`), one `test_epicN_*` method per epic, TC-IDs from `TASKS_AND_TEST_CASES.md` kept as inline comments for traceability. `setUpClass` seeds shared masters (a test Company, sheds, breeds) once; because ERPNext's `Company` controller commits internally (default warehouse/account creation), it needs an explicit `frappe.delete_doc(..., force=1)` in `tearDownClass` rather than relying on transaction rollback. Every behavior change needs a test added or updated here — this is a hard rule, not a suggestion. For UI-facing changes (new buttons, new client scripts), test-suite green is necessary but not sufficient: actually click the thing in a real browser before documenting it in `USER_GUIDE.md`. This caught two real bugs earlier in the project's life (`frm.call()` missing `doc: frm.doc`, and an invalid icon name) that a syntax-only check would have missed.

## Concurrent editing

This bench is sometimes edited by more than one Claude Code session at once (the same repo, checked out once, multiple agents working in parallel). Before a large edit to a shared file (esp. anything under `docs/`, `poultry_daily_log.*`, `poultry_batch.*`, or the workspace JSON), re-read it immediately before editing — the Edit tool will refuse a stale read, which is a feature, not a bug: it means someone else already changed the file. If it keeps happening on the same file, do a read-modify-write in one Bash/Python step instead of a Read-then-Edit round trip. When splitting work across subagents, give each one an explicit list of files it may *not* touch, scoped to what's shared with the coordinator or other subagents.

## Naming

`autoname` uses curly-brace format strings (`"format:PB-{YYYY}-{#####}"` with `"naming_rule": "Expression (old style)"`), not the dot-separated naming-series syntax (`.YYYY.-.#####`) — the latter produces literal, un-rendered names and duplicate-key errors on the second insert. This has bitten the project before; don't reintroduce it.

## Icons

This Frappe version ships three icon sets (`lucide`, `espresso`, `timeless`). Verify an icon name exists before using it: `grep 'id="icon-<name>"' apps/frappe/frappe/public/icons/*/icons.svg`. Invalid names fail silently in the UI rather than erroring at migrate time.
