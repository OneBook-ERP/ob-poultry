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
			"width": 140,
		},
		{"label": _("Housing Type"), "fieldname": "housing_type", "fieldtype": "Data", "width": 120},
		{"label": _("Location"), "fieldname": "location", "fieldtype": "Data", "width": 160},
		{"label": _("Capacity (Birds)"), "fieldname": "capacity", "fieldtype": "Int", "width": 120},
		{
			"label": _("Default Feed Warehouse"),
			"fieldname": "default_feed_warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 160,
		},
		{
			"label": _("Default Egg Warehouse"),
			"fieldname": "default_egg_warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 160,
		},
	]


def get_data():
	return frappe.db.sql(
		"""
		select s.name, s.housing_type, s.location, s.capacity, s.default_feed_warehouse, s.default_egg_warehouse
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
