import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import flt


def after_migrate():
	setup_custom_fields()
	setup_poultry_item_groups()
	setup_default_item_group_mappings()
	setup_default_egg_cold_room()


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


def setup_default_egg_cold_room():
	"""Ensures Egg Cold Room warehouse and default settings exist for all active companies."""
	default_wh_candidate = None
	for company in frappe.get_all("Company", fields=["name", "abbr"]):
		wh_name = f"Egg Cold Room - {company.abbr}"
		if not frappe.db.exists("Warehouse", wh_name):
			parent_wh = f"All Warehouses - {company.abbr}"
			if frappe.db.exists("Warehouse", parent_wh):
				wh_doc = frappe.get_doc(
					{
						"doctype": "Warehouse",
						"warehouse_name": "Egg Cold Room",
						"parent_warehouse": parent_wh,
						"company": company.name,
						"is_group": 0,
					}
				).insert(ignore_permissions=True)
				if not default_wh_candidate:
					default_wh_candidate = wh_doc.name
		else:
			if not default_wh_candidate:
				default_wh_candidate = wh_name

	if not frappe.db.exists("DocType", "Poultry Settings"):
		return

	settings = frappe.get_single("Poultry Settings")
	save_settings = False
	if not settings.default_egg_warehouse and default_wh_candidate:
		settings.default_egg_warehouse = default_wh_candidate
		save_settings = True

	if not settings.default_egg_item:
		egg_item = frappe.db.get_value("Item", {"name": "Table Egg", "is_stock_item": 1}, "name")
		if not egg_item:
			egg_item = frappe.db.get_value(
				"Item",
				{
					"item_group": ("in", ["Eggs", "Egg", "Products"]),
					"is_stock_item": 1,
					"name": ("like", "%Egg%"),
				},
				"name",
			)
		if egg_item:
			settings.default_egg_item = egg_item
			save_settings = True

	if not settings.auto_post_egg_stock_entry:
		settings.auto_post_egg_stock_entry = 1
		save_settings = True

	if save_settings:
		settings.flags.ignore_permissions = True
		settings.save()

	# Link default_egg_warehouse to active sheds if empty
	if default_wh_candidate:
		for shed in frappe.get_all("Poultry Shed", fields=["name", "default_egg_warehouse"]):
			if not shed.default_egg_warehouse:
				frappe.db.set_value("Poultry Shed", shed.name, "default_egg_warehouse", default_wh_candidate)

	# Ensure Table Egg and Cracked Egg have standard valuation rates if 0
	if frappe.db.exists("Item", "Table Egg") and not flt(
		frappe.db.get_value("Item", "Table Egg", "valuation_rate")
	):
		frappe.db.set_value("Item", "Table Egg", "valuation_rate", 5.0)
	if frappe.db.exists("Item", "Cracked Egg") and not flt(
		frappe.db.get_value("Item", "Cracked Egg", "valuation_rate")
	):
		frappe.db.set_value("Item", "Cracked Egg", "valuation_rate", 2.5)


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
