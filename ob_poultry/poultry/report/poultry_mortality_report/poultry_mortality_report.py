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
			"label": _("Batch"),
			"fieldname": "batch",
			"fieldtype": "Link",
			"options": "Poultry Batch",
			"width": 130,
		},
		{
			"label": _("Shed"),
			"fieldname": "shed",
			"fieldtype": "Link",
			"options": "Poultry Shed",
			"width": 120,
		},
		{
			"label": _("Breed"),
			"fieldname": "breed",
			"fieldtype": "Link",
			"options": "Poultry Breed",
			"width": 120,
		},
		{"label": _("Cause"), "fieldname": "cause", "fieldtype": "Data", "width": 140},
		{"label": _("Sex"), "fieldname": "sex", "fieldtype": "Data", "width": 90},
		{"label": _("Count"), "fieldname": "count", "fieldtype": "Int", "width": 80},
		{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 250},
	]


def get_data(filters):
	conditions = ["d.docstatus = 1", "d.log_date between %(from_date)s and %(to_date)s"]
	values = {"from_date": filters.get("from_date"), "to_date": filters.get("to_date")}

	if filters.get("batch"):
		conditions.append("d.batch = %(batch)s")
		values["batch"] = filters.get("batch")
	if filters.get("shed"):
		conditions.append("b.shed = %(shed)s")
		values["shed"] = filters.get("shed")
	if filters.get("breed"):
		conditions.append("b.breed = %(breed)s")
		values["breed"] = filters.get("breed")
	if filters.get("cause"):
		conditions.append("m.cause = %(cause)s")
		values["cause"] = filters.get("cause")

	return frappe.db.sql(
		f"""
		select
			d.log_date,
			d.batch,
			b.shed,
			b.breed,
			m.cause,
			m.sex,
			m.count,
			m.description
		from `tabPoultry Daily Log Mortality Entry` m
		inner join `tabPoultry Daily Log` d on d.name = m.parent
		inner join `tabPoultry Batch` b on b.name = d.batch
		where {" and ".join(conditions)}
		order by d.log_date desc
		""",
		values,
		as_dict=True,
	)
