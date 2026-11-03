import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():
	setup_custom_fields()


def setup_custom_fields():
	custom_fields = {
		"Sales Order Item": [
			{
				"fieldname": "poultry_batch",
				"label": "Poultry Batch",
				"fieldtype": "Link",
				"options": "Poultry Batch",
				"insert_after": "fg_item_qty",
				"in_list_view": 1,
				"columns": 2,
			},
			{
				"fieldname": "poultry_shed",
				"label": "Poultry Shed",
				"fieldtype": "Link",
				"options": "Poultry Shed",
				"insert_after": "poultry_batch",
			},
		],
		"Delivery Note Item": [
			{
				"fieldname": "poultry_batch",
				"label": "Poultry Batch",
				"fieldtype": "Link",
				"options": "Poultry Batch",
				"insert_after": "has_item_scanned",
				"in_list_view": 1,
				"columns": 2,
			},
			{
				"fieldname": "poultry_shed",
				"label": "Poultry Shed",
				"fieldtype": "Link",
				"options": "Poultry Shed",
				"insert_after": "poultry_batch",
			},
		],
		"Sales Invoice Item": [
			{
				"fieldname": "poultry_batch",
				"label": "Poultry Batch",
				"fieldtype": "Link",
				"options": "Poultry Batch",
				"insert_after": "has_item_scanned",
				"in_list_view": 1,
				"columns": 2,
			},
			{
				"fieldname": "poultry_shed",
				"label": "Poultry Shed",
				"fieldtype": "Link",
				"options": "Poultry Shed",
				"insert_after": "poultry_batch",
			},
		],
	}
	create_custom_fields(custom_fields, update=True)
