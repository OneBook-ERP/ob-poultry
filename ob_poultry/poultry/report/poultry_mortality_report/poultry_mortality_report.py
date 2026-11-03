import frappe
from frappe import _
from frappe.utils import cint


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
			"width": 130,
		},
		{
			"label": _("Breed"),
			"fieldname": "breed",
			"fieldtype": "Link",
			"options": "Poultry Breed",
			"width": 120,
		},
		{"label": _("Cause"), "fieldname": "cause", "fieldtype": "Data", "width": 160},
		{"label": _("Opening Birds"), "fieldname": "opening_birds", "fieldtype": "Int", "width": 110},
		{"label": _("Mortality"), "fieldname": "dead", "fieldtype": "Int", "width": 90},
		{"label": _("Culled"), "fieldname": "culled", "fieldtype": "Int", "width": 80},
		{"label": _("Closing Birds"), "fieldname": "closing_birds", "fieldtype": "Int", "width": 110},
		{
			"label": _("Daily Mortality %"),
			"fieldname": "mortality_pct",
			"fieldtype": "Percent",
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
		conditions.append("f.batch = %(batch)s")
		values["batch"] = filters.get("batch")
	if filters.get("shed"):
		conditions.append("f.shed = %(shed)s")
		values["shed"] = filters.get("shed")
	if filters.get("breed"):
		conditions.append("b.breed = %(breed)s")
		values["breed"] = filters.get("breed")
	if filters.get("cause"):
		conditions.append("f.mortality_cause = %(cause)s")
		values["cause"] = filters.get("cause")

	where_clause = " and ".join(conditions)

	rows = frappe.db.sql(
		f"""
		select
			d.log_date,
			f.shed,
			f.batch,
			b.breed,
			f.mortality_cause as cause,
			f.opening_birds,
			f.dead,
			f.culled,
			f.closing_birds
		from `tabPoultry Daily Log Flock Entry` f
		inner join `tabPoultry Daily Log` d on d.name = f.parent
		left join `tabPoultry Batch` b on b.name = f.batch
		where {where_clause} and (f.dead > 0 or f.culled > 0)
		order by d.log_date desc, f.batch asc
		""",
		values,
		as_dict=True,
	)

	# Also check legacy mortality entries if rows are empty and table exists
	if not rows and frappe.db.table_exists("Poultry Daily Log Mortality Entry"):
		legacy_cond = ["d.docstatus = 1", "d.log_date between %(from_date)s and %(to_date)s"]
		if filters.get("batch"):
			legacy_cond.append("d.batch = %(batch)s")
		if filters.get("cause"):
			legacy_cond.append("m.cause = %(cause)s")
		rows = frappe.db.sql(
			f"""
			select
				d.log_date,
				b.shed,
				d.batch,
				b.breed,
				m.cause,
				b.initial_bird_count as opening_birds,
				m.count as dead,
				0 as culled,
				b.current_bird_count as closing_birds
			from `tabPoultry Daily Log Mortality Entry` m
			inner join `tabPoultry Daily Log` d on d.name = m.parent
			left join `tabPoultry Batch` b on b.name = d.batch
			where {" and ".join(legacy_cond)}
			order by d.log_date desc
			""",
			values,
			as_dict=True,
		)

	for row in rows:
		opening = cint(row.opening_birds)
		dead = cint(row.dead)
		row.mortality_pct = round((dead / opening * 100), 2) if opening > 0 else 0.0

	return rows
