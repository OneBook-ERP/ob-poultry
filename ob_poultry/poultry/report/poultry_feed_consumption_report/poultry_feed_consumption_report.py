import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "log_date", "fieldtype": "Date", "width": 100},
		{"label": _("Batch"), "fieldname": "batch", "fieldtype": "Link", "options": "Poultry Batch", "width": 140},
		{"label": _("Feed Item"), "fieldname": "feed_item", "fieldtype": "Link", "options": "Item", "width": 160},
		{"label": _("Feed Consumed (kg)"), "fieldname": "feed_consumed_kg", "fieldtype": "Float", "width": 140},
		{"label": _("Cumulative in Range (kg)"), "fieldname": "cumulative_feed_kg", "fieldtype": "Float", "width": 170},
	]


def get_data(filters):
	conditions = ["docstatus = 1", "feed_consumed_kg > 0", "log_date between %(from_date)s and %(to_date)s"]
	if filters.get("batch"):
		conditions.append("batch = %(batch)s")

	rows = frappe.db.sql(
		f"""
		select batch, log_date, feed_item, feed_consumed_kg
		from `tabPoultry Daily Log`
		where {" and ".join(conditions)}
		order by batch, log_date
		""",
		filters,
		as_dict=True,
	)

	running_total = {}
	for row in rows:
		running_total[row.batch] = running_total.get(row.batch, 0) + (row.feed_consumed_kg or 0)
		row["cumulative_feed_kg"] = running_total[row.batch]

	return rows
