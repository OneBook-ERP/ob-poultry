# AI Agent Guidelines

## 1. Git Push Restrictions (STRICT)
- **NEVER push git commits to remote repositories automatically.**
- All \git push\ actions must be explicitly requested and executed by the USER.
- Do NOT run \git push\, \git push origin\, or any equivalent command on behalf of the user unless the user directly and explicitly instructs you to push in that turn.
- The agent may inspect git status, create commits locally when approved, or create/format diffs, but the user maintains complete control over pushing to remotes.

## 2. Frappe Skills Requirement
- Always consult and follow the Frappe skills located in \/home/frappe/.agents/skills/\:
  - \rappe-app-dev  - \rappe-code-review  - \code-style  - \deep-app-audit  - \ui-design- Adhere strictly to Frappe best practices:
  - Do NOT use raw SQL where Frappe ORM (\rappe.db.get_value\, \rappe.get_doc\, \rappe.db.set_value\, \rappe.db.set_single_value\) is available.
  - Follow Frappe linter and formatting rules (Ruff, Prettier, Semgrep).
  - Use proper hooks, DocType schemas, and client-side Frappe events.

## 3. General Pair-Programming Rules
- Do not make destructive git changes (\git reset --hard\, \git rebase -i\, force pushes) without explicit user consent.
- Keep the user informed before performing multi-file edits or refactoring.

## 4. Never auto execute the plan
- When you have a plan, always ask for user approval before executing it.
