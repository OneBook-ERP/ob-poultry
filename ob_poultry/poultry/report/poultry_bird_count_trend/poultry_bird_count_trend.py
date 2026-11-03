import frappe
from frappe import _
from frappe.utils import cint, date_diff, getdate


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "log_date", "fieldtype": "Date", "width": 100},
		{"label": _("Age (Days)"), "fieldname": "age_days", "fieldtype": "Int", "width": 90},
		{"label": _("Age (Weeks)"), "fieldname": "age_weeks", "fieldtype": "Int", "width": 95},
		{"label": _("Mortality"), "fieldname": "mortality_count", "fieldtype": "Int", "width": 90},
		{"label": _("Mortality Cause"), "fieldname": "mortality_cause", "fieldtype": "Data", "width": 140},
		{"label": _("Cull"), "fieldname": "cull_count", "fieldtype": "Int", "width": 80},
		{"label": _("Removed (Cum)"), "fieldname": "removed_cum", "fieldtype": "Int", "width": 120},
		{"label": _("Bird Count"), "fieldname": "bird_count", "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	batch_name = filters.get("batch")
	if not batch_name:
		return []

	batch = frappe.db.get_value(
		"Poultry Batch",
		batch_name,
		["initial_bird_count", "start_date", "placement_age_weeks", "placement_age_days"],
		as_dict=True,
	)
	if not batch:
		return []

	placement_days = (cint(batch.placement_age_weeks or 0) * 7) + cint(batch.placement_age_days or 0)

	# First check flock entries
	flock_logs = frappe.db.sql(
		"""
		select
			d.log_date,
			f.dead as mortality_count,
			f.mortality_cause,
			f.culled as cull_count,
			f.closing_birds as bird_count
		from `tabPoultry Daily Log Flock Entry` f
		inner join `tabPoultry Daily Log` d on d.name = f.parent
		where f.batch = %(batch)s and d.docstatus = 1
		order by d.log_date asc
		""",
		{"batch": batch_name},
		as_dict=True,
	)

	if flock_logs:
		logs = flock_logs
	else:
		logs = frappe.db.sql(
			"""
			select
				log_date,
				mortality_count,
				'' as mortality_cause,
				cull_count,
				null as bird_count
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
		m = log.mortality_count or 0
		c = log.cull_count or 0
		removed_cum += m + c
		log_date = getdate(log.log_date)
		if from_date and log_date < from_date:
			continue
		if to_date and log_date > to_date:
			continue

		age_days = date_diff(log.log_date, batch.start_date) + placement_days
		age_weeks = int(age_days // 7)

		cur_birds = log.bird_count if log.bird_count is not None else (batch.initial_bird_count - removed_cum)

		rows.append(
			{
				"log_date": log.log_date,
				"age_days": age_days,
				"age_weeks": age_weeks,
				"mortality_count": m,
				"mortality_cause": log.mortality_cause or "",
				"cull_count": c,
				"removed_cum": removed_cum,
				"bird_count": max(0, cur_birds),
			}
		)

	return rows
