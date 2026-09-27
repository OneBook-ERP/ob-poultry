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
		{"label": _("Feed Cost"), "fieldname": "feed_cost", "fieldtype": "Currency", "width": 120},
		{"label": _("Cumulative Cost in Range"), "fieldname": "cumulative_feed_cost", "fieldtype": "Currency", "width": 180},
	]


def get_data(filters):
	conditions = ["d.docstatus = 1", "d.feed_consumed_kg > 0", "d.log_date between %(from_date)s and %(to_date)s"]
	if filters.get("batch"):
		conditions.append("d.batch = %(batch)s")

	rows = frappe.db.sql(
		f"""
		select d.batch, d.log_date, d.feed_item, d.feed_consumed_kg, sed.amount as feed_cost
		from `tabPoultry Daily Log` d
		left join `tabStock Entry Detail` sed
			on sed.parent = d.stock_entry and sed.item_code = d.feed_item
		where {" and ".join(conditions)}
		order by d.batch, d.log_date
		""",
		filters,
		as_dict=True,
	)

	running_total = {}
	running_cost = {}
	for row in rows:
		running_total[row.batch] = running_total.get(row.batch, 0) + (row.feed_consumed_kg or 0)
		running_cost[row.batch] = running_cost.get(row.batch, 0) + (row.feed_cost or 0)
		row["cumulative_feed_kg"] = running_total[row.batch]
		row["cumulative_feed_cost"] = running_cost[row.batch]

	return rows
