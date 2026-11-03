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
		{"label": _("Week / Day"), "fieldname": "week_day", "fieldtype": "Data", "width": 110},
		{"label": _("Good Eggs"), "fieldname": "good_eggs", "fieldtype": "Int", "width": 100},
		{"label": _("Double Yolk"), "fieldname": "double_yolk_eggs", "fieldtype": "Int", "width": 100},
		{"label": _("Broken"), "fieldname": "broken_eggs", "fieldtype": "Int", "width": 90},
		{"label": _("Waste"), "fieldname": "waste_eggs", "fieldtype": "Int", "width": 90},
		{
			"label": _("Total Produced"),
			"fieldname": "total_eggs",
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"label": _("HDEP %"),
			"fieldname": "egg_production_pct",
			"fieldtype": "Percent",
			"precision": 2,
			"width": 90,
		},
		{
			"label": _("HHEP %"),
			"fieldname": "hhep_pct",
			"fieldtype": "Percent",
			"precision": 2,
			"width": 90,
		},
		{
			"label": _("Broken %"),
			"fieldname": "broken_egg_pct",
			"fieldtype": "Percent",
			"precision": 2,
			"width": 90,
		},
		{"label": _("Tray Summary"), "fieldname": "tray_summary", "fieldtype": "Data", "width": 150},
		{
			"label": _("Feed Cost/Egg"),
			"fieldname": "feed_cost_per_egg",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Water (L)"),
			"fieldname": "water_consumption_liters",
			"fieldtype": "Float",
			"precision": 1,
			"width": 90,
		},
		{
			"label": _("Lighting (Hrs)"),
			"fieldname": "lighting_hours",
			"fieldtype": "Float",
			"precision": 1,
			"width": 100,
		},
	]


def get_data(filters):
	conditions = ["d.docstatus = 1", "d.log_date between %(from_date)s and %(to_date)s"]
	values = {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
	}
	if filters.get("batch"):
		conditions.append("e.batch = %(batch)s")
		values["batch"] = filters.get("batch")
	if filters.get("shed"):
		conditions.append("e.shed = %(shed)s")
		values["shed"] = filters.get("shed")

	where_clause = " and ".join(conditions)

	return frappe.db.sql(
		f"""
		select
			d.log_date,
			e.shed,
			e.batch,
			e.week_day,
			e.good_eggs,
			e.double_yolk_eggs,
			e.broken_eggs,
			e.waste_eggs,
			e.total_eggs,
			e.egg_production_pct,
			e.hhep_pct,
			e.broken_egg_pct,
			e.tray_summary,
			d.feed_cost_per_egg,
			d.water_consumption_liters,
			d.lighting_hours
		from `tabPoultry Daily Log` d
		inner join `tabPoultry Daily Log Egg Entry` e on e.parent = d.name
		where {where_clause}
		order by d.log_date desc, e.batch asc
		""",
		values,
		as_dict=True,
	)
