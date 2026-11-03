import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from ob_poultry.api import get_egg_rate
from ob_poultry.poultry.controllers.sales_custom import validate_sales_order


class TestSalesAndEggRate(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		# Ensure test daily egg rate exists
		existing = frappe.db.get_value("Poultry Daily Egg Rate", {"rate_date": nowdate(), "market": "Namakkal"}, "name")
		if existing:
			frappe.db.set_value("Poultry Daily Egg Rate", existing, {
				"rate_per_piece": 5.70,
				"rate_per_tray": 171.0,
				"rate_per_100": 570.0,
				"rate_per_peti": 1197.0,
				"national_average": 6.16,
				"trend": "Stable",
			})
		else:
			frappe.get_doc(
				{
					"doctype": "Poultry Daily Egg Rate",
					"rate_date": nowdate(),
					"market": "Namakkal",
					"rate_per_piece": 5.70,
					"rate_per_tray": 171.0,
					"rate_per_100": 570.0,
					"rate_per_peti": 1197.0,
					"national_average": 6.16,
					"trend": "Stable",
				}
			).insert(ignore_permissions=True)

	def test_get_egg_rate_api(self):
		# Default piece rate
		res = get_egg_rate(market="Namakkal", date=nowdate())
		self.assertTrue(res.get("success"))
		self.assertEqual(res.get("rate_per_piece"), 5.70)
		self.assertEqual(res.get("rate"), 5.70)
		self.assertEqual(res.get("uom"), "Piece")

		# Tray rate
		res_tray = get_egg_rate(market="Namakkal", date=nowdate(), uom="Tray")
		self.assertEqual(res_tray.get("rate"), 171.0)
		self.assertEqual(res_tray.get("uom"), "Tray")

		# Peti rate
		res_peti = get_egg_rate(market="Namakkal", date=nowdate(), uom="Peti")
		self.assertEqual(res_peti.get("rate"), 1197.0)
		self.assertEqual(res_peti.get("uom"), "Peti")

		# 100 rate
		res_100 = get_egg_rate(market="Namakkal", date=nowdate(), uom="100")
		self.assertEqual(res_100.get("rate"), 570.0)
		self.assertEqual(res_100.get("uom"), "100")

	def test_sales_order_delivery_date_sync(self):
		mock_doc = frappe._dict(
			{
				"doctype": "Sales Order",
				"delivery_date": "2026-11-15",
				"items": [
					frappe._dict({"delivery_date": None, "item_code": "Table Egg"}),
					frappe._dict({"delivery_date": "2026-11-10", "item_code": "Table Egg"}),
				],
			}
		)
		validate_sales_order(mock_doc)
		for item in mock_doc.get("items"):
			self.assertEqual(item.delivery_date, "2026-11-15")
