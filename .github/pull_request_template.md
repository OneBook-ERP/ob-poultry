## Summary

<!-- What changes and why. Link the issue: Fixes #123 -->

## Checklist

- [ ] Targets `develop`; commit subjects follow `type(scope): subject`
- [ ] Tests added or updated in `ob_poultry/tests/test_poultry_module.py` and passing
- [ ] Permission checks on every new whitelisted method
- [ ] Computed values stay derived from submitted rows (no parallel editable fields)
- [ ] Patches are idempotent and listed in `patches.txt`
- [ ] ERPNext and Frappe are not edited; changes go through hooks or custom fields
- [ ] `docs/` updated if requirements, scope or a user-visible flow changed
