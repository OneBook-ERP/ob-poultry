# Copyright (c) 2026, OB and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate, nowdate

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
