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
		{"label": _("Date"), "fieldname": "log_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Shed"),
			"fieldname": "shed",
			"fieldtype": "Link",
			"options": "Poultry Shed",
			"width": 120,
		},
		{
			"label": _("Batch"),
			"fieldname": "batch",
			"fieldtype": "Link",
			"options": "Poultry Batch",
			"width": 140,
		},
		{
			"label": _("Feed Item"),
			"fieldname": "feed_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{
			"label": _("Feed Consumed (kg)"),
			"fieldname": "feed_spent_kg",
			"fieldtype": "Float",
			"precision": 2,
			"width": 140,
		},
		{
			"label": _("Grams / Bird (g)"),
			"fieldname": "feed_spent_g_per_bird",
			"fieldtype": "Float",
			"precision": 1,
			"width": 120,
		},
		{"label": _("Feed Cost"), "fieldname": "total_feed_cost", "fieldtype": "Currency", "width": 110},
		{
			"label": _("Cumulative Feed (kg)"),
			"fieldname": "cumulative_feed_kg",
			"fieldtype": "Float",
			"precision": 2,
			"width": 150,
		},
		{
			"label": _("Water (L)"),
			"fieldname": "water_consumption_liters",
			"fieldtype": "Float",
			"precision": 1,
			"width": 90,
		},
		{
			"label": _("Water:Feed Ratio"),
			"fieldname": "water_feed_ratio",
			"fieldtype": "Float",
			"precision": 2,
			"width": 120,
		},
	]


def get_data(filters):
	conditions = ["d.docstatus = 1", "d.log_date between %(from_date)s and %(to_date)s"]
	values = {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
	}

	if filters.get("batch"):
		conditions.append("fe.batch = %(batch)s")
		values["batch"] = filters.get("batch")
	if filters.get("shed"):
		conditions.append("fe.shed = %(shed)s")
		values["shed"] = filters.get("shed")

	where_clause = " and ".join(conditions)

	rows = frappe.db.sql(
		f"""
		select
			d.log_date,
			fe.shed,
			fe.batch,
			fe.feed_item,
			fe.feed_spent_kg,
			fe.feed_spent_g_per_bird,
			fe.total_feed_cost,
			d.water_consumption_liters,
			d.water_feed_ratio
		from `tabPoultry Daily Log Feed Entry` fe
		inner join `tabPoultry Daily Log` d on d.name = fe.parent
		where {where_clause} and fe.feed_spent_kg > 0
		order by fe.batch, d.log_date asc
		""",
		values,
		as_dict=True,
	)

	# If no feed entries, fallback to legacy parent fields
	if not rows:
		p_cond = [
			"d.docstatus = 1",
			"d.feed_consumed_kg > 0",
			"d.log_date between %(from_date)s and %(to_date)s",
		]
		if filters.get("batch"):
			p_cond.append("d.batch = %(batch)s")
		rows = frappe.db.sql(
			f"""
			select
				d.log_date,
				b.shed,
				d.batch,
				d.feed_item,
				d.feed_consumed_kg as feed_spent_kg,
				0 as feed_spent_g_per_bird,
				d.total_feed_cost,
				d.water_consumption_liters,
				d.water_feed_ratio
			from `tabPoultry Daily Log` d
			left join `tabPoultry Batch` b on b.name = d.batch
			where {" and ".join(p_cond)}
			order by d.batch, d.log_date asc
			""",
			values,
			as_dict=True,
		)

	running_total = {}
	for row in rows:
		b = row.batch or "Unknown"
		running_total[b] = running_total.get(b, 0.0) + flt(row.feed_spent_kg)
		row["cumulative_feed_kg"] = round(running_total[b], 2)

	return rows
