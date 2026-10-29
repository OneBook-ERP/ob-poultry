import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Hatchery"),
			"fieldname": "hatchery",
			"fieldtype": "Link",
			"options": "Poultry Hatchery",
			"width": 160,
		},
		{"label": _("Hatches"), "fieldname": "hatch_count", "fieldtype": "Int", "width": 90},
		{"label": _("Total Eggs Set"), "fieldname": "total_eggs_set", "fieldtype": "Int", "width": 120},
		{
			"label": _("Total Estimated Chicks"),
			"fieldname": "total_estimated_chicks",
			"fieldtype": "Int",
			"width": 150,
		},
		{
			"label": _("Total Actual Chicks"),
			"fieldname": "total_actual_chicks",
			"fieldtype": "Int",
			"width": 140,
		},
		{
			"label": _("Hatchability %"),
			"fieldname": "hatchability_pct",
			"fieldtype": "Percent",
			"precision": 2,
			"width": 120,
		},
	]


def get_data(filters):
	conditions = ["1=1"]
	values = {}

	if filters.get("hatchery"):
		conditions.append("hatchery = %(hatchery)s")
		values["hatchery"] = filters["hatchery"]

	if filters.get("from_date"):
		conditions.append("schedule_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("schedule_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	where_clause = " and ".join(conditions)

	rows = frappe.db.sql(
		f"""
		select
			hatchery,
			count(*) as hatch_count,
			sum(eggs_set) as total_eggs_set,
			sum(estimated_chicks) as total_estimated_chicks,
			sum(actual_chicks) as total_actual_chicks
		from `tabPoultry Hatch`
		where {where_clause}
		group by hatchery
		order by hatchery
		""",
		values,
		as_dict=True,
	)

	for row in rows:
		total_eggs_set = row.total_eggs_set or 0
		total_actual_chicks = row.total_actual_chicks or 0
		row.hatchability_pct = (total_actual_chicks / total_eggs_set * 100) if total_eggs_set else 0

	return rows
