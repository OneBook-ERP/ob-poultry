# Copyright (c) 2026, OB and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, nowdate

from ob_poultry.poultry.utils.mkisan_api import fetch_and_store_egg_rates, get_today_egg_rate


class IntegrationTestPoultryDailyEggRate(IntegrationTestCase):
	def setUp(self):
		settings = frappe.get_single("Poultry Settings")
		settings.enable_mkisan_sync = 1
		settings.default_egg_market = "Namakkal"
		settings.save(ignore_permissions=True)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit

	def test_fetch_and_store_egg_rates(self):
		res = fetch_and_store_egg_rates(market="Namakkal", force=True)
		self.assertTrue(res.get("success"), f"Fetch failed: {res.get('message')}")
		self.assertEqual(res.get("market"), "Namakkal")
		self.assertGreater(flt(res.get("rate_per_piece")), 0)
		self.assertGreater(flt(res.get("rate_per_tray")), 0)

		# Check DB record
		rate_date = str(res.get("rate_date"))
		rec = frappe.get_doc("Poultry Daily Egg Rate", f"{rate_date}-Namakkal")
		self.assertEqual(str(rec.rate_date), rate_date)
		self.assertEqual(rec.market, "Namakkal")
		self.assertEqual(flt(rec.rate_per_piece), flt(res.get("rate_per_piece")))

	def test_cache_first_lookup(self):
		# Ensure a record exists
		fetch_and_store_egg_rates(market="Namakkal", force=True)

		# Second call with force=False must be cached
		cached_res = fetch_and_store_egg_rates(market="Namakkal", force=False)
		self.assertTrue(cached_res.get("success"))
		self.assertTrue(cached_res.get("cached"), "Expected cached=True to conserve API quota")

	def test_get_today_egg_rate_api(self):
		fetch_and_store_egg_rates(market="Namakkal", force=True)
		rate_info = get_today_egg_rate(market="Namakkal")
		self.assertTrue(rate_info.get("success"))
		self.assertEqual(rate_info.get("market"), "Namakkal")
		self.assertGreater(flt(rate_info.get("rate_per_piece")), 0)
		self.assertGreater(flt(rate_info.get("rate_per_tray")), 0)
