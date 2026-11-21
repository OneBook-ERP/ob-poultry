# Contributing to ob_poultry

## Branches

| Branch | Purpose |
|---|---|
| `main` | Released code: what production sites run. Changed only by a pull request from `develop` (or a hotfix). |
| `develop` | Integration branch. Every feature and fix pull request targets `develop`. |
| `feat/<topic>`, `fix/<topic>`, `chore/<topic>` | Short-lived work branches, cut from `develop`. |

`main` and `develop` are protected: no direct pushes, no force pushes, no deletions. Changes land through a pull request with passing checks, one approval and resolved review conversations. Contributors working from a fork open their pull request against `OneBook-ERP/ob-poultry:develop`.

## Commits

Use conventional commit subjects, `type(scope): subject`, for example `fix(daily-log): ...`. Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert. CI checks this on every pull request.

## Before you push

```bash
pip install pre-commit
pre-commit install          # runs ruff, prettier and eslint on each commit
pre-commit run --all-files  # the same checks CI runs
```

## Tests

Every behavior change adds or updates a test in `ob_poultry/tests/test_poultry_module.py`, with TC-IDs from `docs/TASKS_AND_TEST_CASES.md` as comments:

```bash
bench --site <test-site> run-tests --app ob_poultry
```

Run tests on a test site, not on a site holding real farm data. For UI changes, also click the feature in a browser before documenting it in `docs/USER_GUIDE.md`.

## Docs

`docs/` is the source of truth for requirements and scope. Update `BRD.md`, `FIT_GAP_ANALYSIS.md`, `FRD.md`, `ROADMAP.md` and `TASKS_AND_TEST_CASES.md` when scope changes.

## Continuous integration

- **Linters** (every pull request): pre-commit, Frappe's Semgrep rules, commit subjects.
- **Server Tests**: installs ERPNext and ob_poultry on a fresh site, migrates, and runs the test suite.
- **CodeRabbit** reviews each pull request against the rules in `.coderabbit.yaml`.

A pull request is merged when the checks pass and a maintainer has approved it.
