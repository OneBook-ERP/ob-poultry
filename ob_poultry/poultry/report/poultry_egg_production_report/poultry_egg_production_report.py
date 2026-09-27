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
		{"label": _("Grade"), "fieldname": "grade", "fieldtype": "Data", "width": 110},
		{"label": _("Opening Count"), "fieldname": "opening_count", "fieldtype": "Int", "width": 110},
		{"label": _("Production Count"), "fieldname": "production_count", "fieldtype": "Int", "width": 120},
		{"label": _("Closing Count"), "fieldname": "closing_count", "fieldtype": "Int", "width": 110},
		{"label": _("Avg Weight (g)"), "fieldname": "avg_weight_g", "fieldtype": "Float", "width": 120},
		{"label": _("Total Eggs (Day)"), "fieldname": "total_eggs_produced", "fieldtype": "Int", "width": 120},
		{"label": _("HDEP %"), "fieldname": "hdep_percent", "fieldtype": "Percent", "precision": 2, "width": 90},
	]


def get_data(filters):
	conditions = ["d.docstatus = 1", "d.log_date between %(from_date)s and %(to_date)s"]
	if filters.get("batch"):
		conditions.append("d.batch = %(batch)s")
	if filters.get("grade"):
		conditions.append("e.grade = %(grade)s")

	return frappe.db.sql(
		f"""
		select
			d.log_date,
			d.batch,
			e.grade,
			e.opening_count,
			e.production_count,
			e.closing_count,
			e.avg_weight_g,
			d.total_eggs_produced,
			d.hdep_percent
		from `tabPoultry Daily Log` d
		inner join `tabPoultry Daily Log Egg Entry` e on e.parent = d.name
		where {" and ".join(conditions)}
		order by d.batch, d.log_date, e.grade
		""",
		filters,
		as_dict=True,
	)
