import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Hatch"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Poultry Hatch",
			"width": 140,
		},
		{
			"label": _("Hatchery"),
			"fieldname": "hatchery",
			"fieldtype": "Link",
			"options": "Poultry Hatchery",
			"width": 150,
		},
		{"label": _("Eggs Set"), "fieldname": "initial_egg_count", "fieldtype": "Int", "width": 100},
		{"label": _("Hatched Chicks"), "fieldname": "hatched_egg", "fieldtype": "Int", "width": 120},
		{"label": _("Move to Stock"), "fieldname": "move_to_stock", "fieldtype": "Int", "width": 110},
		{"label": _("Wasted Eggs"), "fieldname": "wasted_eggs", "fieldtype": "Int", "width": 100},
		{"label": _("Chicks Transferred"), "fieldname": "transferred", "fieldtype": "Int", "width": 130},
		{"label": _("Chick Balance"), "fieldname": "balance", "fieldtype": "Int", "width": 110},
	]


def get_data(filters):
	conditions = ["(hatched_egg is not null or actual_chicks is not null)"]
	values = {}

	if filters.get("hatchery"):
		conditions.append("hatchery = %(hatchery)s")
		values["hatchery"] = filters["hatchery"]

	where_clause = " and ".join(conditions)

	hatches = frappe.db.sql(
		f"""
		select
			name,
			hatchery,
			coalesce(initial_egg_count, eggs_set, 0) as initial_egg_count,
			coalesce(hatched_egg, actual_chicks, 0) as hatched_egg,
			coalesce(move_to_stock, 0) as move_to_stock,
			coalesce(wasted_eggs, 0) as wasted_eggs
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
		hatch.balance = (cint(hatch.hatched_egg) or 0) - transferred

	return hatches
