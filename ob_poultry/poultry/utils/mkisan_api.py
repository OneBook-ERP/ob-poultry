# Copyright (c) 2026, OB and contributors
# For license information, please see license.txt

import json
import os
import urllib.request
import urllib.error
import frappe
from frappe import _
from frappe.utils import flt, now_datetime, nowdate, getdate

MKISAN_BASE_URL = "https://mkisan.net/wp-json/mkisan/v1"

def get_mkisan_api_key():
	"""
	Retrieves the MKisan API key prioritizing:
	1. frappe.conf / site_config.json
	2. os.environ
	3. AES-256 encrypted Password field in Poultry Settings
	"""
	key = frappe.conf.get("mkisan_api_key") or os.environ.get("MKISAN_API_KEY")
	if key:
		return key.strip()

	try:
		decrypted = frappe.utils.password.get_decrypted_password(
			"Poultry Settings", "Poultry Settings", "mkisan_api_key", raise_exception=False
		)
		if decrypted:
			return decrypted.strip()
	except Exception:
		pass

	return None


@frappe.whitelist()
def fetch_and_store_egg_rates(market=None, force=False, override=False):
	"""
	Queries the MKisan API for NECC egg rates and records them into Poultry Daily Egg Rate.
	If today's rate for this market already exists in the database, skips the external API call
	and immediately returns already updated.
	"""
	settings = frappe.get_single("Poultry Settings")
	target_market = (market or settings.default_egg_market or "Namakkal").strip()
	today = getdate(nowdate())

	# 1. Check if today's rate already exists in local database
	existing = frappe.db.get_value(
		"Poultry Daily Egg Rate",
		{"rate_date": today, "market": target_market},
		["name", "rate_date", "market", "rate_per_piece", "rate_per_tray", "rate_per_100", "rate_per_peti", "national_average", "trend", "synced_at"],
		as_dict=True,
	)

	# 2. If today's rate is already recorded and not an emergency override, skip API call
	if existing and not override:
		date_str = format_date(existing.rate_date) if "format_date" in dir() else str(existing.rate_date)
		return {
			"success": True,
			"cached": True,
			"already_updated": True,
			"rate_date": str(existing.rate_date),
			"market": target_market,
			"rate_per_piece": flt(existing.rate_per_piece),
			"rate_per_tray": flt(existing.rate_per_tray),
			"trend": existing.trend,
			"message": _("Today's rate ({0}) for {1} is already fetched and up to date.").format(date_str, target_market),
		}

	if not settings.enable_mkisan_sync and not override:
		return {"success": False, "message": _("MKisan sync is disabled in Poultry Settings.")}

	api_key = get_mkisan_api_key()
	headers = {
		"User-Agent": "OneBook-Poultry/1.0 (ERPNext; contact: support@onebook.local)",
		"Accept": "application/json",
	}
	if api_key:
		headers["X-API-Key"] = api_key

	# We attempt the market-specific route first
	market_slug = target_market.lower().replace(" ", "").replace(".", "")
	urls_to_try = [
		f"{MKISAN_BASE_URL}/egg-rate/{market_slug}",
		f"{MKISAN_BASE_URL}/egg-rate",
	]

	data = None
	last_error = None

	for url in urls_to_try:
		try:
			req = urllib.request.Request(url, headers=headers)
			with urllib.request.urlopen(req, timeout=12) as response:
				remaining = response.headers.get("X-RateLimit-Remaining")
				if remaining is not None and flt(remaining) < 5:
					frappe.log_error(
						title="MKisan API Quota Warning",
						message=f"Only {remaining} requests remaining today for MKisan API.",
					)

				raw_bytes = response.read()
				data = json.loads(raw_bytes.decode("utf-8"))
				if data:
					break
		except urllib.error.HTTPError as e:
			last_error = f"HTTP {e.code}: {e.reason}"
			continue
		except Exception as e:
			last_error = str(e)
			continue

	if not data:
		msg = f"Failed to fetch egg rate for {target_market}. Error: {last_error}"
		frappe.log_error(title="MKisan Sync Error", message=msg)
		frappe.db.set_value(
			"Poultry Settings",
			"Poultry Settings",
			{"sync_status": f"Sync failed on {today}: {last_error}"},
		)
		return {"success": False, "message": msg}

	# Parse response
	extracted = parse_mkisan_response(data, target_market)
	if not extracted:
		msg = f"No egg rate data found in response for market {target_market}."
		frappe.log_error(title="MKisan Sync Parse Error", message=f"{msg}\nResponse: {data}")
		return {"success": False, "message": msg}

	rate_date = extracted.get("rate_date") or today
	eggs_per_tray = flt(settings.eggs_per_tray) or 30

	rate_per_piece = flt(extracted.get("piece"))
	rate_per_tray = flt(extracted.get("tray")) or (rate_per_piece * eggs_per_tray)
	rate_per_100 = flt(extracted.get("hundred_pcs")) or (rate_per_piece * 100)
	rate_per_peti = flt(extracted.get("peti")) or (rate_per_piece * 210)
	trend = (extracted.get("trend") or "Stable").capitalize()
	if trend not in ("Up", "Down", "Stable"):
		trend = "Stable"

	national_avg = flt(extracted.get("national_average"))

	# Upsert into Poultry Daily Egg Rate
	doc_name = f"{rate_date}-{target_market}"
	if frappe.db.exists("Poultry Daily Egg Rate", doc_name):
		doc = frappe.get_doc("Poultry Daily Egg Rate", doc_name)
	else:
		doc = frappe.new_doc("Poultry Daily Egg Rate")
		doc.rate_date = rate_date
		doc.market = target_market

	doc.rate_per_piece = rate_per_piece
	doc.rate_per_tray = rate_per_tray
	doc.rate_per_100 = rate_per_100
	doc.rate_per_peti = rate_per_peti
	doc.trend = trend
	doc.national_average = national_avg
	doc.synced_at = now_datetime()
	doc.source = "MKisan NECC API"
	doc.flags.ignore_permissions = True
	doc.save()

	# Update Poultry Settings audit fields
	status_msg = f"Synced {target_market} rate on {now_datetime().strftime('%d-%m-%Y %I:%M %p')} (₹{flt(rate_per_piece):.2f}/egg)"
	frappe.db.set_value(
		"Poultry Settings",
		"Poultry Settings",
		{
			"last_egg_rate_sync": now_datetime(),
			"sync_status": status_msg,
		},
	)
	frappe.db.commit()

	return {
		"success": True,
		"cached": False,
		"rate_date": rate_date,
		"market": target_market,
		"rate_per_piece": rate_per_piece,
		"rate_per_tray": rate_per_tray,
		"trend": trend,
	}


def parse_mkisan_response(data, target_market):
	"""
	Handles both single market object format and list format from MKisan endpoints.
	"""
	if not data:
		return None

	# Single market response: {"success": true, "market": "Delhi", "today_rate": {...}, "comparison": {...}}
	if isinstance(data, dict):
		if "today_rate" in data and isinstance(data["today_rate"], dict):
			tr = data["today_rate"]
			comp = data.get("comparison") or {}
			return {
				"rate_date": tr.get("date"),
				"piece": tr.get("piece"),
				"tray": tr.get("tray"),
				"hundred_pcs": tr.get("hundred_pcs"),
				"peti": tr.get("peti"),
				"trend": tr.get("trend"),
				"national_average": comp.get("avg_national"),
			}

		# Alternative: data is in "data" key: {"success": true, "data": {"rate": 5.85, "rate_per_tray": ...}}
		if "data" in data and isinstance(data["data"], dict) and "rate" in data["data"]:
			d = data["data"]
			return {
				"rate_date": d.get("date"),
				"piece": d.get("rate"),
				"tray": d.get("rate_per_tray"),
				"hundred_pcs": d.get("rate_per_100"),
				"trend": "Stable",
			}

		# Rates array in response: {"success": true, "rates": [...]}
		if "rates" in data and isinstance(data["rates"], list):
			for item in data["rates"]:
				m = (item.get("market") or "").lower()
				if m == target_market.lower() or target_market.lower() in m:
					return {
						"rate_date": item.get("date"),
						"piece": item.get("piece"),
						"tray": item.get("tray"),
						"hundred_pcs": item.get("hundred_pcs"),
						"peti": item.get("peti"),
						"trend": item.get("trend"),
					}

	return None


@frappe.whitelist()
def get_today_egg_rate(market=None, date=None):
	"""
	Frontend whitelisted API.
	Returns today's rate or the latest available rate for the given market.
	Never blocks or throws an error; returns safe fallback.
	"""
	settings = frappe.get_single("Poultry Settings")
	target_market = (market or settings.default_egg_market or "Namakkal").strip()
	target_date = getdate(date) if date else getdate(nowdate())

	# 1. Look for exact date and market in local database
	record = frappe.db.get_value(
		"Poultry Daily Egg Rate",
		{"rate_date": target_date, "market": target_market},
		["rate_date", "market", "rate_per_piece", "rate_per_tray", "rate_per_100", "rate_per_peti", "national_average", "trend", "synced_at"],
		as_dict=True,
	)

	# 2. If not found and target_date is today, attempt a live fetch
	if not record and target_date == getdate(nowdate()):
		res = fetch_and_store_egg_rates(market=target_market, force=False)
		if res.get("success"):
			record = frappe.db.get_value(
				"Poultry Daily Egg Rate",
				{"rate_date": target_date, "market": target_market},
				["rate_date", "market", "rate_per_piece", "rate_per_tray", "rate_per_100", "rate_per_peti", "national_average", "trend", "synced_at"],
				as_dict=True,
			)

	# 3. If still not found (e.g. morning trade before 1:30 PM declaration),
	# retrieve the most recent available rate for this market
	is_fallback = False
	if not record:
		record = frappe.db.get_value(
			"Poultry Daily Egg Rate",
			{"market": target_market, "rate_date": ("<=", target_date)},
			["rate_date", "market", "rate_per_piece", "rate_per_tray", "rate_per_100", "rate_per_peti", "national_average", "trend", "synced_at"],
			order_by="rate_date desc",
			as_dict=True,
		)
		is_fallback = bool(record)

	if record:
		return {
			"success": True,
			"is_fallback": is_fallback,
			"rate_date": str(record.rate_date),
			"market": record.market,
			"rate_per_piece": flt(record.rate_per_piece),
			"rate_per_tray": flt(record.rate_per_tray),
			"rate_per_100": flt(record.rate_per_100),
			"rate_per_peti": flt(record.rate_per_peti),
			"national_average": flt(record.national_average),
			"trend": record.trend,
			"synced_at": str(record.synced_at) if record.synced_at else None,
		}

	return {
		"success": False,
		"message": _("No egg rate record found for market {0}.").format(target_market),
	}


def scheduled_fetch_egg_rates():
	"""
	Cron job scheduled daily at 1:30 PM IST (post-NECC publication).
	Checks if today's rate is already in the database; if yes, skips API call.
	"""
	settings = frappe.get_single("Poultry Settings")
	if not settings.enable_mkisan_sync:
		return

	today = getdate(nowdate())
	market = settings.default_egg_market or "Namakkal"
	if frappe.db.exists("Poultry Daily Egg Rate", {"rate_date": today, "market": market}):
		return

	fetch_and_store_egg_rates(market=market, force=False)


def scheduled_backup_fetch_egg_rates():
	"""
	Secondary retry scheduled daily at 2:15 PM IST.
	Runs only if today's rate was not recorded by the 1:30 PM run.
	"""
	settings = frappe.get_single("Poultry Settings")
	if not settings.enable_mkisan_sync:
		return

	today = getdate(nowdate())
	market = settings.default_egg_market or "Namakkal"
	if frappe.db.exists("Poultry Daily Egg Rate", {"rate_date": today, "market": market}):
		return

	fetch_and_store_egg_rates(market=market, force=False)
