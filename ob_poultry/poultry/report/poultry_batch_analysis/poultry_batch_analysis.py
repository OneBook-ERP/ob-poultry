import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Batch"), "fieldname": "name", "fieldtype": "Link", "options": "Poultry Batch", "width": 130},
		{"label": _("Shed"), "fieldname": "shed", "fieldtype": "Link", "options": "Poultry Shed", "width": 110},
		{"label": _("Breed"), "fieldname": "breed", "fieldtype": "Link", "options": "Poultry Breed", "width": 110},
		{"label": _("Flock Source"), "fieldname": "flock_source", "fieldtype": "Data", "width": 100},
		{"label": _("Farmer"), "fieldname": "farmer", "fieldtype": "Link", "options": "Poultry Farmer", "width": 130},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 80},
		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
		{"label": _("Initial Birds"), "fieldname": "initial_bird_count", "fieldtype": "Int", "width": 100},
		{"label": _("Current Birds"), "fieldname": "current_bird_count", "fieldtype": "Int", "width": 110},
		{"label": _("Total Mortality"), "fieldname": "total_mortality", "fieldtype": "Int", "width": 110},
		{"label": _("Feed Consumed (kg)"), "fieldname": "cumulative_feed_kg", "fieldtype": "Float", "precision": 2, "width": 140},
		{"label": _("FCR"), "fieldname": "fcr", "fieldtype": "Float", "precision": 3, "width": 90},
		{"label": _("CFCR"), "fieldname": "cfcr", "fieldtype": "Float", "precision": 3, "width": 90},
		{"label": _("Growing Charge Amount"), "fieldname": "growing_charge_amount", "fieldtype": "Currency", "width": 150},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("from_date"):
		conditions.append("start_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")
	if filters.get("to_date"):
		conditions.append("start_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")
	if filters.get("flock_source"):
		conditions.append("flock_source = %(flock_source)s")
		values["flock_source"] = filters.get("flock_source")
	if filters.get("status"):
		conditions.append("status = %(status)s")
		values["status"] = filters.get("status")

	where_clause = f"where {' and '.join(conditions)}" if conditions else ""

	return frappe.db.sql(
		f"""
		select
			name, shed, breed, flock_source, farmer, status, start_date,
			initial_bird_count, current_bird_count, total_mortality,
			cumulative_feed_kg, fcr, cfcr, growing_charge_amount
		from `tabPoultry Batch`
		{where_clause}
		order by start_date desc
		""",
		values,
		as_dict=True,
	)
