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
			"label": _("Batch"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Poultry Batch",
			"width": 130,
		},
		{
			"label": _("Farmer"),
			"fieldname": "farmer",
			"fieldtype": "Link",
			"options": "Poultry Farmer",
			"width": 140,
		},
		{
			"label": _("Scheme"),
			"fieldname": "growing_charge_scheme",
			"fieldtype": "Link",
			"options": "Poultry Growing Charge Scheme",
			"width": 160,
		},
		{
			"label": _("Shed"),
			"fieldname": "shed",
			"fieldtype": "Link",
			"options": "Poultry Shed",
			"width": 120,
		},
		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
		{"label": _("Initial Birds"), "fieldname": "initial_bird_count", "fieldtype": "Int", "width": 100},
		{"label": _("Current Birds"), "fieldname": "current_bird_count", "fieldtype": "Int", "width": 100},
		{"label": _("Mortality"), "fieldname": "total_mortality", "fieldtype": "Int", "width": 90},
		{"label": _("FCR"), "fieldname": "fcr", "fieldtype": "Float", "precision": 3, "width": 90},
		{"label": _("CFCR"), "fieldname": "cfcr", "fieldtype": "Float", "precision": 3, "width": 90},
		{
			"label": _("Growing Charge Amount"),
			"fieldname": "growing_charge_amount",
			"fieldtype": "Currency",
			"width": 160,
		},
	]


def get_data(filters):
	conditions = ["flock_source = 'Contract'"]
	values = {}

	if filters.get("farmer"):
		conditions.append("farmer = %(farmer)s")
		values["farmer"] = filters["farmer"]

	if filters.get("growing_charge_scheme"):
		conditions.append("growing_charge_scheme = %(growing_charge_scheme)s")
		values["growing_charge_scheme"] = filters["growing_charge_scheme"]

	if filters.get("from_date"):
		conditions.append("start_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("start_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	where_clause = " and ".join(conditions)

	return frappe.db.sql(
		f"""
		select
			name, farmer, growing_charge_scheme, shed, start_date,
			initial_bird_count, current_bird_count, total_mortality,
			fcr, cfcr, growing_charge_amount
		from `tabPoultry Batch`
		where {where_clause}
		order by start_date desc
		""",
		values,
		as_dict=True,
	)
