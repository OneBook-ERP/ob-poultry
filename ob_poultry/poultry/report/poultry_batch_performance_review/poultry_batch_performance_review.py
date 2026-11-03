import frappe
from frappe import _
from frappe.utils import flt


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
			"label": _("Shed"),
			"fieldname": "shed",
			"fieldtype": "Link",
			"options": "Poultry Shed",
			"width": 110,
		},
		{"label": _("Housing Type"), "fieldname": "housing_type", "fieldtype": "Data", "width": 110},
		{
			"label": _("Breed"),
			"fieldname": "breed",
			"fieldtype": "Link",
			"options": "Poultry Breed",
			"width": 110,
		},
		{"label": _("Flock Source"), "fieldname": "flock_source", "fieldtype": "Data", "width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 80},
		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
		{"label": _("Age / Week"), "fieldname": "batch_week", "fieldtype": "Data", "width": 120},
		{"label": _("Initial Birds"), "fieldname": "initial_bird_count", "fieldtype": "Int", "width": 100},
		{"label": _("Current Birds"), "fieldname": "current_bird_count", "fieldtype": "Int", "width": 110},
		{
			"label": _("Mortality %"),
			"fieldname": "mortality_pct",
			"fieldtype": "Percent",
			"precision": 2,
			"width": 100,
		},
		{
			"label": _("Feed Consumed (kg)"),
			"fieldname": "cumulative_feed_kg",
			"fieldtype": "Float",
			"precision": 2,
			"width": 130,
		},
		{"label": _("FCR"), "fieldname": "fcr", "fieldtype": "Float", "precision": 3, "width": 80},
		{"label": _("CFCR"), "fieldname": "cfcr", "fieldtype": "Float", "precision": 3, "width": 80},
		{
			"label": _("Total Eggs"),
			"fieldname": "cumulative_eggs_produced",
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"label": _("EHH"),
			"fieldname": "cumulative_ehh",
			"fieldtype": "Float",
			"precision": 1,
			"width": 80,
		},
		{
			"label": _("Avg HHEP %"),
			"fieldname": "avg_hhep_pct",
			"fieldtype": "Percent",
			"precision": 2,
			"width": 100,
		},
		{
			"label": _("Feed Cost/Egg"),
			"fieldname": "avg_feed_cost_per_egg",
			"fieldtype": "Currency",
			"width": 110,
		},
		{
			"label": _("Growing Charges"),
			"fieldname": "growing_charge_amount",
			"fieldtype": "Currency",
			"width": 130,
		},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("status"):
		conditions.append("b.status = %(status)s")
		values["status"] = filters.get("status")
	if filters.get("flock_source"):
		conditions.append("b.flock_source = %(flock_source)s")
		values["flock_source"] = filters.get("flock_source")
	if filters.get("shed"):
		conditions.append("b.shed = %(shed)s")
		values["shed"] = filters.get("shed")

	where_clause = f"where {' and '.join(conditions)}" if conditions else ""

	rows = frappe.db.sql(
		f"""
		select
			b.name, b.shed, s.housing_type, b.breed, b.flock_source, b.status, b.start_date,
			b.batch_week, b.initial_bird_count, b.current_bird_count, b.total_mortality,
			b.cumulative_feed_kg, b.fcr, b.cfcr,
			b.cumulative_eggs_produced, b.cumulative_ehh, b.avg_hhep_pct, b.avg_feed_cost_per_egg,
			b.growing_charge_amount
		from `tabPoultry Batch` b
		left join `tabPoultry Shed` s on s.name = b.shed
		{where_clause}
		order by b.start_date desc
		""",
		values,
		as_dict=True,
	)

	for row in rows:
		row.mortality_pct = (
			flt(row.total_mortality) / flt(row.initial_bird_count) * 100 if row.initial_bird_count else 0
		)

	return rows
