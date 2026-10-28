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
			"fieldname": "batch",
			"fieldtype": "Link",
			"options": "Poultry Batch",
			"width": 140,
		},
		{"label": _("Eggs Produced"), "fieldname": "total_eggs_produced", "fieldtype": "Int", "width": 130},
		{"label": _("Feed Cost"), "fieldname": "feed_cost", "fieldtype": "Currency", "width": 130},
		{"label": _("Cost per Egg"), "fieldname": "cost_per_egg", "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = ["d.docstatus = 1", "d.log_date between %(from_date)s and %(to_date)s"]
	if filters.get("batch"):
		conditions.append("d.batch = %(batch)s")

	rows = frappe.db.sql(
		f"""
		select d.batch,
			sum(d.total_eggs_produced) as total_eggs_produced,
			sum(sed.amount) as feed_cost
		from `tabPoultry Daily Log` d
		left join `tabStock Entry Detail` sed
			on sed.parent = d.stock_entry and sed.item_code = d.feed_item
		where {" and ".join(conditions)}
		group by d.batch
		order by d.batch
		""",
		filters,
		as_dict=True,
	)

	for row in rows:
		row["feed_cost"] = row.feed_cost or 0
		row["cost_per_egg"] = (row.feed_cost / row.total_eggs_produced) if row.total_eggs_produced else 0

	return rows
