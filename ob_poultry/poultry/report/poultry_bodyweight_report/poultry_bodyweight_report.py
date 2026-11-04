import frappe
from frappe import _
from frappe.utils import cint, date_diff


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "log_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Batch"),
			"fieldname": "batch",
			"fieldtype": "Link",
			"options": "Poultry Batch",
			"width": 140,
		},
		{"label": _("Age (Days)"), "fieldname": "age_days", "fieldtype": "Int", "width": 90},
		{"label": _("Age (Weeks)"), "fieldname": "age_weeks", "fieldtype": "Int", "width": 95},
		{
			"label": _("Body Weight (g)"),
			"fieldname": "average_body_weight_g",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": _("Standard Body Weight (g)"),
			"fieldname": "std_body_weight_g",
			"fieldtype": "Float",
			"width": 160,
		},
		{"label": _("Diff (g)"), "fieldname": "diff_g", "fieldtype": "Float", "width": 100},
	]


def get_data(filters):
	from ob_poultry.poultry.doctype.poultry_daily_log.poultry_daily_log import get_benchmark_for_age

	conditions = [
		"d.docstatus = 1",
		"d.log_date between %(from_date)s and %(to_date)s",
	]
	batch_condition = "and d.batch = %(batch)s" if filters.get("batch") else ""
	flock_batch_condition = "and fe.batch = %(batch)s" if filters.get("batch") else ""

	child_rows = frappe.db.sql(
		f"""
		select
			fe.parent as name, fe.batch, d.log_date, fe.average_body_weight_g,
			b.start_date, b.placement_age_weeks, b.placement_age_days, b.breed, b.breed_type
		from `tabPoultry Daily Log Flock Entry` fe
		inner join `tabPoultry Daily Log` d on d.name = fe.parent
		inner join `tabPoultry Batch` b on b.name = fe.batch
		where {" and ".join(conditions)} and fe.average_body_weight_g > 0 {flock_batch_condition}
		order by fe.batch, d.log_date
		""",
		filters,
		as_dict=True,
	)

	parent_rows = frappe.db.sql(
		f"""
		select
			d.name, d.batch, d.log_date, d.average_body_weight_g, d.std_body_weight_g,
			b.start_date, b.placement_age_weeks, b.placement_age_days, b.breed, b.breed_type
		from `tabPoultry Daily Log` d
		inner join `tabPoultry Batch` b on b.name = d.batch
		where {" and ".join(conditions)} and d.average_body_weight_g > 0 {batch_condition}
		order by d.batch, d.log_date
		""",
		filters,
		as_dict=True,
	)

	seen = set()
	combined = []
	for r in child_rows:
		key = (r.name, r.batch)
		seen.add(key)
		combined.append(r)

	for r in parent_rows:
		key = (r.name, r.batch)
		if key not in seen:
			combined.append(r)

	for row in combined:
		placement_days = (cint(row.placement_age_weeks or 0) * 7) + cint(row.placement_age_days or 0)
		age_days = date_diff(row.log_date, row.start_date) + placement_days
		row["age_days"] = age_days
		row["age_weeks"] = int(age_days // 7)
		if not row.get("std_body_weight_g") and row.get("breed"):
			bmk = get_benchmark_for_age(row.breed, age_days, row.get("breed_type"))
			row["std_body_weight_g"] = bmk.get("standard_body_weight_g") if bmk else None
		row["diff_g"] = (
			(row.average_body_weight_g - row.std_body_weight_g) if row.get("std_body_weight_g") else None
		)

	combined.sort(key=lambda x: (x.batch or "", x.log_date))
	return combined
