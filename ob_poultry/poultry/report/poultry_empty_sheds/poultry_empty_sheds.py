import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data()
	return columns, data


def get_columns():
	return [
		{
			"label": _("Shed"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Poultry Shed",
			"width": 150,
		},
		{"label": _("Location"), "fieldname": "location", "fieldtype": "Data", "width": 200},
		{"label": _("Capacity (Birds)"), "fieldname": "capacity", "fieldtype": "Int", "width": 130},
	]


def get_data():
	return frappe.db.sql(
		"""
		select s.name, s.location, s.capacity
		from `tabPoultry Shed` s
		where s.is_active = 1
		and not exists (
			select 1 from `tabPoultry Batch` b
			where b.shed = s.name and b.status = 'Active'
		)
		order by s.name
		""",
		as_dict=True,
	)
