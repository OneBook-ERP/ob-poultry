import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Hatch"), "fieldname": "name", "fieldtype": "Link", "options": "Poultry Hatch", "width": 140},
		{"label": _("Hatchery"), "fieldname": "hatchery", "fieldtype": "Link", "options": "Poultry Hatchery", "width": 160},
		{"label": _("Actual Chicks"), "fieldname": "actual_chicks", "fieldtype": "Int", "width": 120},
		{"label": _("Transferred"), "fieldname": "transferred", "fieldtype": "Int", "width": 110},
		{"label": _("Balance"), "fieldname": "balance", "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	conditions = ["actual_chicks is not null"]
	values = {}

	if filters.get("hatchery"):
		conditions.append("hatchery = %(hatchery)s")
		values["hatchery"] = filters["hatchery"]

	where_clause = " and ".join(conditions)

	hatches = frappe.db.sql(
		f"""
		select name, hatchery, actual_chicks
		from `tabPoultry Hatch`
		where {where_clause}
		order by hatchery, name
		""",
		values,
		as_dict=True,
	)

	if not hatches:
		return []

	hatch_names = [h.name for h in hatches]
	transfer_rows = frappe.db.sql(
		"""
		select hatch, sum(quantity) as transferred
		from `tabPoultry Chick Transfer`
		where docstatus = 1 and hatch in %(hatches)s
		group by hatch
		""",
		{"hatches": hatch_names},
		as_dict=True,
	)
	transferred_map = {row.hatch: row.transferred or 0 for row in transfer_rows}

	for hatch in hatches:
		transferred = transferred_map.get(hatch.name, 0)
		hatch.transferred = transferred
		hatch.balance = (hatch.actual_chicks or 0) - transferred

	return hatches
