import frappe
from frappe import _
from frappe.utils import date_diff, getdate


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "log_date", "fieldtype": "Date", "width": 100},
		{"label": _("Age (Days)"), "fieldname": "age_days", "fieldtype": "Int", "width": 90},
		{"label": _("Mortality"), "fieldname": "mortality_count", "fieldtype": "Int", "width": 90},
		{"label": _("Cull"), "fieldname": "cull_count", "fieldtype": "Int", "width": 80},
		{"label": _("Removed (Cum)"), "fieldname": "removed_cum", "fieldtype": "Int", "width": 120},
		{"label": _("Bird Count"), "fieldname": "bird_count", "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	batch_name = filters.get("batch")
	if not batch_name:
		return []

	batch = frappe.db.get_value(
		"Poultry Batch", batch_name, ["initial_bird_count", "start_date"], as_dict=True
	)
	if not batch:
		return []

	logs = frappe.db.sql(
		"""
		select log_date, mortality_count, cull_count
		from `tabPoultry Daily Log`
		where batch = %(batch)s and docstatus = 1
		order by log_date asc
		""",
		{"batch": batch_name},
		as_dict=True,
	)

	from_date = getdate(filters.get("from_date")) if filters.get("from_date") else None
	to_date = getdate(filters.get("to_date")) if filters.get("to_date") else None

	removed_cum = 0
	rows = []
	for log in logs:
		removed_cum += (log.mortality_count or 0) + (log.cull_count or 0)
		log_date = getdate(log.log_date)
		if from_date and log_date < from_date:
			continue
		if to_date and log_date > to_date:
			continue
		rows.append(
			{
				"log_date": log.log_date,
				"age_days": date_diff(log.log_date, batch.start_date),
				"mortality_count": log.mortality_count or 0,
				"cull_count": log.cull_count or 0,
				"removed_cum": removed_cum,
				"bird_count": batch.initial_bird_count - removed_cum,
			}
		)

	return rows
