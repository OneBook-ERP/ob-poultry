import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():
	setup_custom_fields()
	setup_poultry_item_groups()
	setup_default_item_group_mappings()


def setup_poultry_item_groups():
	"""Creates default standard Poultry item groups under All Item Groups if missing."""
	if not frappe.db.exists("Item Group", "All Item Groups"):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": "All Item Groups", "is_group": 1}).insert(
			ignore_permissions=True
		)

	if not frappe.db.exists("Item Group", "Poultry"):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "Poultry",
				"parent_item_group": "All Item Groups",
				"is_group": 1,
			}
		).insert(ignore_permissions=True)

	child_groups = [
		{"item_group_name": "Feed & Raw Materials", "is_group": 1},
		{"item_group_name": "Eggs", "is_group": 0},
		{"item_group_name": "Live Birds", "is_group": 0},
		{"item_group_name": "Medicines & Vaccines", "is_group": 0},
		{"item_group_name": "Poultry By-Products", "is_group": 0},
	]

	for g in child_groups:
		if not frappe.db.exists("Item Group", g["item_group_name"]):
			frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": g["item_group_name"],
					"parent_item_group": "Poultry",
					"is_group": g["is_group"],
				}
			).insert(ignore_permissions=True)


def setup_default_item_group_mappings():
	"""Seeds default place-to-item-group mappings in Poultry Settings if empty."""
	if not frappe.db.exists("DocType", "Poultry Settings"):
		return

	settings = frappe.get_single("Poultry Settings")
	if settings.get("item_group_mappings") and len(settings.item_group_mappings) > 0:
		return

	defaults = [
		{
			"place": "Feed Items",
			"item_group": "Feed & Raw Materials",
			"description": "Finished feed & daily feeding",
		},
		{
			"place": "Feed Raw Materials",
			"item_group": "Feed & Raw Materials",
			"description": "Raw feed milling ingredients",
		},
		{
			"place": "Egg Items",
			"item_group": "Eggs",
			"description": "Egg collections & unhatched returns",
		},
		{
			"place": "Live Bird Items",
			"item_group": "Live Birds",
			"description": "Chicks, broilers, & layer pullets",
		},
		{
			"place": "Poultry Sales Items",
			"item_group": "Eggs",
			"description": "Commercial egg sales",
		},
		{
			"place": "Poultry Sales Items",
			"item_group": "Feed & Raw Materials",
			"description": "Feed & grain sales",
		},
		{
			"place": "Poultry Sales Items",
			"item_group": "Live Birds",
			"description": "Live bird & cull bird sales",
		},
		{
			"place": "Poultry Sales Items",
			"item_group": "Poultry By-Products",
			"description": "Manure & empty bag sales",
		},
		{
			"place": "Medicines & Vaccines",
			"item_group": "Medicines & Vaccines",
			"description": "Health & biosecurity supplies",
		},
	]

	for d in defaults:
		if frappe.db.exists("Item Group", d["item_group"]):
			settings.append("item_group_mappings", d)

	settings.flags.ignore_permissions = True
	settings.save()


def setup_custom_fields():
	live_bird_fields = [
		{
			"fieldname": "is_weight_based_live_bird_sale",
			"label": "Weight-Based Live Bird Sale",
			"fieldtype": "Check",
			"default": "0",
			"insert_after": "poultry_shed",
		},
		{
			"fieldname": "gross_weight_kg",
			"label": "Gross Weight (kg)",
			"fieldtype": "Float",
			"insert_after": "is_weight_based_live_bird_sale",
			"depends_on": "eval:doc.is_weight_based_live_bird_sale",
		},
		{
			"fieldname": "tare_weight_kg",
			"label": "Tare Weight (kg)",
			"fieldtype": "Float",
			"insert_after": "gross_weight_kg",
			"depends_on": "eval:doc.is_weight_based_live_bird_sale",
		},
		{
			"fieldname": "net_weight_kg",
			"label": "Net Weight (kg)",
			"fieldtype": "Float",
			"read_only": 1,
			"insert_after": "tare_weight_kg",
			"depends_on": "eval:doc.is_weight_based_live_bird_sale",
		},
		{
			"fieldname": "birds_count",
			"label": "Bird Count (Cull Birds)",
			"fieldtype": "Int",
			"insert_after": "net_weight_kg",
			"depends_on": "eval:doc.is_weight_based_live_bird_sale",
		},
		{
			"fieldname": "avg_bird_weight_kg",
			"label": "Avg Bird Weight (kg)",
			"fieldtype": "Float",
			"read_only": 1,
			"insert_after": "birds_count",
			"depends_on": "eval:doc.is_weight_based_live_bird_sale",
		},
	]

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
			*live_bird_fields,
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
			*live_bird_fields,
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
			*live_bird_fields,
		],
	}
	create_custom_fields(custom_fields, update=True)
