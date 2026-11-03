# Copyright (c) 2026, OB and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt, getdate, nowdate

from ob_poultry.poultry.utils.mkisan_api import (
	fetch_and_store_egg_rates,
)
from ob_poultry.poultry.utils.mkisan_api import (
	get_today_egg_rate as fetch_egg_rate,
)


@frappe.whitelist(methods=["GET", "POST"])
def get_egg_rate(
	market: str | None = None,
	date: str | None = None,
	uom: str | None = None,
	item_code: str | None = None,
) -> dict:
	"""Public Whitelisted API to fetch NECC egg rates.

	Returns market rate per piece, per tray (30), per 100, and per peti (210),
	along with unit-specific rate matching the given UOM or item_code.
	"""
	data = fetch_egg_rate(market=market, date=date)
	if not data or not data.get("success"):
		return {"success": False, "message": "Failed to fetch egg rate"}

	target_uom = (uom or "").strip().lower()
	if not target_uom and item_code:
		item_uom = frappe.db.get_value("Item", item_code, "stock_uom")
		if item_uom:
			target_uom = item_uom.strip().lower()

	# Determine matching rate for the UOM
	unit_rate = flt(data.get("rate_per_piece"))
	matched_uom = "Piece"

	if target_uom in ["tray", "trays"]:
		unit_rate = flt(data.get("rate_per_tray"))
		matched_uom = "Tray"
	elif target_uom in ["peti", "petis", "box", "boxes", "carton", "cartons"]:
		unit_rate = flt(data.get("rate_per_peti"))
		matched_uom = "Peti"
	elif target_uom in ["100", "hundred", "cent"]:
		unit_rate = flt(data.get("rate_per_100"))
		matched_uom = "100"
	elif target_uom in ["nos", "piece", "pieces", "unit", "units", "egg", "eggs"]:
		unit_rate = flt(data.get("rate_per_piece"))
		matched_uom = "Piece"

	data["uom"] = matched_uom
	data["rate"] = unit_rate
	data["suggested_rate"] = unit_rate
	return data


@frappe.whitelist(methods=["POST"])
def sync_egg_rates(market: str | None = None, force: bool = False) -> dict:
	"""Fetch and store latest egg rates from MKisan/NECC immediately."""
	return fetch_and_store_egg_rates(market=market, force=force)


@frappe.whitelist(methods=["GET"])
def get_egg_rate_summary() -> dict:
	"""Return today's rates across key poultry markets."""
	target_date = getdate(nowdate())
	markets = ["Namakkal", "Bengaluru", "Hyderabad", "Delhi", "Mumbai", "Kolkata"]
	rates = frappe.get_all(
		"Poultry Daily Egg Rate",
		filters={"rate_date": target_date, "market": ["in", markets]},
		fields=[
			"market",
			"rate_per_piece",
			"rate_per_tray",
			"rate_per_peti",
			"trend",
		],
	)
	return {"date": str(target_date), "rates": rates}


@frappe.whitelist(methods=["GET", "POST"])
def get_batch_egg_stock(batch: str) -> dict:
	"""Return total eggs produced, sold, and available for a given Poultry Batch."""
	if not batch:
		return {"eggs_left": 0, "trays": 0, "rem_eggs": 0, "summary": "0 eggs"}

	batch_doc = frappe.db.get_value(
		"Poultry Batch",
		batch,
		["name", "batch_name", "shed", "status"],
		as_dict=True,
	)
	if not batch_doc:
		return {"eggs_left": 0, "trays": 0, "rem_eggs": 0, "summary": "0 eggs"}

	batch_title = batch_doc.get("batch_name") or batch_doc.get("name")

	# Fetch total produced eggs for this batch from Poultry Daily Log Egg Entry
	pdl_egg = frappe.qb.DocType("Poultry Daily Log Egg Entry")
	pdl = frappe.qb.DocType("Poultry Daily Log")
	prod_query = (
		frappe.qb.from_(pdl_egg)
		.join(pdl)
		.on(pdl.name == pdl_egg.parent)
		.select(
			Sum(pdl_egg.total_eggs).as_("total_produced"),
			Sum(pdl_egg.good_eggs).as_("good_eggs"),
			Sum(pdl_egg.broken_eggs).as_("broken_eggs"),
		)
		.where(pdl_egg.batch == batch)
		.where(pdl.docstatus < 2)
	)
	prod_res = prod_query.run(as_dict=True)
	total_produced = cint(prod_res[0].total_produced) if prod_res and prod_res[0].total_produced else 0

	# Fetch total eggs sold via Daily Log Sales Entry
	pdl_sales = frappe.qb.DocType("Poultry Daily Log Sales Entry")
	sales_query = (
		frappe.qb.from_(pdl_sales)
		.join(pdl)
		.on(pdl.name == pdl_sales.parent)
		.select(
			Sum(pdl_sales.good_eggs + pdl_sales.broken_eggs + pdl_sales.double_yolk_eggs).as_("total_sold")
		)
		.where(pdl_sales.batch == batch)
		.where(pdl.docstatus < 2)
	)
	sales_res = sales_query.run(as_dict=True)
	total_sold = cint(sales_res[0].total_sold) if sales_res and sales_res[0].total_sold else 0

	# Fetch total eggs ordered in submitted / open Sales Orders for this batch
	so_item = frappe.qb.DocType("Sales Order Item")
	so = frappe.qb.DocType("Sales Order")
	so_query = (
		frappe.qb.from_(so_item)
		.join(so)
		.on(so.name == so_item.parent)
		.select(Sum(so_item.qty).as_("so_qty"))
		.where(so_item.poultry_batch == batch)
		.where(so.docstatus == 1)
		.where(so.status.notin(["Completed", "Cancelled", "Closed"]))
	)
	so_res = so_query.run(as_dict=True)
	so_ordered = cint(so_res[0].so_qty) if so_res and so_res[0].so_qty else 0

	eggs_left = max(0, total_produced - total_sold - so_ordered)
	trays = eggs_left // 30
	rem_eggs = eggs_left % 30

	summary = (
		f"{eggs_left:,} eggs ({trays:,} trays, {rem_eggs} eggs)" if eggs_left > 0 else "0 eggs (0 trays)"
	)

	return {
		"batch": batch,
		"batch_name": batch_title,
		"total_produced": total_produced,
		"total_sold": total_sold,
		"eggs_left": eggs_left,
		"trays": trays,
		"rem_eggs": rem_eggs,
		"summary": summary,
	}


def get_child_item_groups(group_name: str) -> list[str]:
	"""Returns the item group itself and all its descendant sub-groups."""
	if not group_name or not frappe.db.exists("Item Group", group_name):
		return [group_name] if group_name else []

	bounds = frappe.db.get_value("Item Group", group_name, ["lft", "rgt"], as_dict=True)
	if not bounds or not bounds.get("lft") or not bounds.get("rgt"):
		return [group_name]

	return frappe.db.get_all(
		"Item Group",
		filters={"lft": (">=", bounds.lft), "rgt": ("<=", bounds.rgt)},
		pluck="name",
	)


@frappe.whitelist()
def get_mapped_item_groups(place: str) -> list[str]:
	"""Returns all configured Item Groups (including children) for a specific place/dropdown."""
	if not place:
		return []

	matched_groups = set()
	if frappe.db.exists("DocType", "Poultry Settings"):
		settings = frappe.get_cached_doc("Poultry Settings")
		for row in settings.get("item_group_mappings", []):
			if row.place == place and row.item_group:
				for child_g in get_child_item_groups(row.item_group):
					matched_groups.add(child_g)

	# Fallbacks if settings table is unpopulated
	if not matched_groups:
		fallback_map = {
			"Feed Items": ["Feed & Raw Materials", "Poultry Feed", "Products"],
			"Feed Raw Materials": ["Feed & Raw Materials", "Raw Material"],
			"Egg Items": ["Eggs"],
			"Live Bird Items": ["Live Birds"],
			"Medicines & Vaccines": ["Medicines & Vaccines"],
			"Poultry Sales Items": [
				"Eggs",
				"Feed & Raw Materials",
				"Live Birds",
				"Poultry By-Products",
			],
		}
		for g in fallback_map.get(place, []):
			if frappe.db.exists("Item Group", g):
				for child_g in get_child_item_groups(g):
					matched_groups.add(child_g)

	return sorted(list(matched_groups))


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query_by_place(doctype, txt, searchfield, start, page_len, filters):
	"""Dynamic Link query for Item fields filtered by Poultry Settings item group mapping."""
	place = (filters or {}).get("place")
	groups = get_mapped_item_groups(place) if place else []

	conditions = ["disabled = 0"]
	params = {}

	if groups:
		placeholders = ", ".join([f"%(g_{i})s" for i in range(len(groups))])
		conditions.append(f"item_group in ({placeholders})")
		for i, g in enumerate(groups):
			params[f"g_{i}"] = g

	if txt:
		conditions.append("(name like %(txt)s or item_name like %(txt)s)")
		params["txt"] = f"%{txt}%"

	where_clause = " and ".join(conditions)

	return frappe.db.sql(
		f"""
		select name, item_name, item_group, stock_uom
		from `tabItem`
		where {where_clause}
		order by idx desc, name asc
		limit %(start)s, %(page_len)s
		""",
		{**params, "start": cint(start), "page_len": cint(page_len)},
		as_list=True,
	)
