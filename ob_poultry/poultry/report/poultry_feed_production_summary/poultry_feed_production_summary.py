import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "creation", "fieldtype": "Date", "width": 100},
		{
			"label": _("Production"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Poultry Feed Production",
			"width": 150,
		},
		{
			"label": _("Formula"),
			"fieldname": "formula",
			"fieldtype": "Link",
			"options": "Poultry Feed Formula",
			"width": 180,
		},
		{"label": _("Feed Item"), "fieldname": "feed_item", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": _("Planned Batches"), "fieldname": "planned_batches", "fieldtype": "Float", "width": 120},
		{"label": _("Planned Qty (kg)"), "fieldname": "planned_qty_kg", "fieldtype": "Float", "width": 130},
		{"label": _("Actual Output (kg)"), "fieldname": "actual_output_kg", "fieldtype": "Float", "width": 130},
		{"label": _("Yield %"), "fieldname": "yield_percent", "fieldtype": "Percent", "precision": 2, "width": 90},
		{
			"label": _("Work Order"),
			"fieldname": "work_order",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 150,
		},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("from_date") and filters.get("to_date"):
		conditions.append("date(p.creation) between %(from_date)s and %(to_date)s")
		values["from_date"] = filters["from_date"]
		values["to_date"] = filters["to_date"]

	if filters.get("formula"):
		conditions.append("p.formula = %(formula)s")
		values["formula"] = filters["formula"]

	where_clause = f"where {' and '.join(conditions)}" if conditions else ""

	return frappe.db.sql(
		f"""
		select
			p.name, p.creation, p.formula, f.feed_item,
			p.planned_batches, p.planned_qty_kg, p.actual_output_kg,
			p.yield_percent, p.work_order
		from `tabPoultry Feed Production` p
		inner join `tabPoultry Feed Formula` f on f.name = p.formula
		{where_clause}
		order by p.creation desc
		""",
		values,
		as_dict=True,
	)
