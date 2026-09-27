import frappe
from frappe import _
from frappe.utils import date_diff


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "log_date", "fieldtype": "Date", "width": 100},
		{"label": _("Batch"), "fieldname": "batch", "fieldtype": "Link", "options": "Poultry Batch", "width": 140},
		{"label": _("Age (Days)"), "fieldname": "age_days", "fieldtype": "Int", "width": 90},
		{"label": _("Body Weight (g)"), "fieldname": "average_body_weight_g", "fieldtype": "Float", "width": 130},
		{"label": _("Standard Body Weight (g)"), "fieldname": "std_body_weight_g", "fieldtype": "Float", "width": 160},
		{"label": _("Diff (g)"), "fieldname": "diff_g", "fieldtype": "Float", "width": 100},
	]


def get_data(filters):
	conditions = ["d.docstatus = 1", "d.average_body_weight_g > 0", "d.log_date between %(from_date)s and %(to_date)s"]
	if filters.get("batch"):
		conditions.append("d.batch = %(batch)s")

	rows = frappe.db.sql(
		f"""
		select d.name, d.batch, d.log_date, d.average_body_weight_g, d.std_body_weight_g, b.start_date
		from `tabPoultry Daily Log` d
		inner join `tabPoultry Batch` b on b.name = d.batch
		where {" and ".join(conditions)}
		order by d.batch, d.log_date
		""",
		filters,
		as_dict=True,
	)

	for row in rows:
		row["age_days"] = date_diff(row.log_date, row.start_date)
		row["diff_g"] = (row.average_body_weight_g - row.std_body_weight_g) if row.std_body_weight_g else None

	return rows
