import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, nowdate


class TestLayerFarming(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		# Ensure Breed
		if not frappe.db.exists("Poultry Breed", "Test Layer Breed"):
			frappe.get_doc(
				{
					"doctype": "Poultry Breed",
					"breed_name": "Test Layer Breed",
					"bird_type": "Layer",
				}
			).insert(ignore_permissions=True)

		# Ensure Shed
		if not frappe.db.exists("Poultry Shed", "Test Layer Shed"):
			frappe.get_doc(
				{
					"doctype": "Poultry Shed",
					"shed_name": "Test Layer Shed",
					"housing_type": "Cage",
					"capacity": 5000,
					"is_active": 1,
				}
			).insert(ignore_permissions=True)

	def test_pullet_placement_age(self):
		"""Test that placement_age_weeks and placement_age_days are factored into batch age."""
		batch = frappe.new_doc("Poultry Batch")
		batch.batch_name = "Test 16-Week Pullet Batch"
		batch.breed = "Test Layer Breed"
		batch.shed = "Test Layer Shed"
		batch.start_date = nowdate()
		batch.initial_bird_count = 1000
		batch.current_bird_count = 1000
		batch.status = "Active"
		batch.placement_age_weeks = 16
		batch.placement_age_days = 2
		batch.save(ignore_permissions=True)

		# Elapsed days is 0 since start_date is today.
		# Placement days: 16 * 7 + 2 = 114 days = 16 weeks, 114 days
		self.assertIn("16 weeks", batch.batch_week)
		self.assertIn("114 days", batch.batch_week)

	def test_daily_log_water_and_layer_kpis(self):
		"""Test water intake metrics, HHEP %, mortality cause, and feed cost per egg."""
		# Create batch
		batch = frappe.new_doc("Poultry Batch")
		batch.batch_name = "Test Layer Daily Log Batch"
		batch.breed = "Test Layer Breed"
		batch.shed = "Test Layer Shed"
		batch.start_date = nowdate()
		batch.initial_bird_count = 1000
		batch.current_bird_count = 1000
		batch.status = "Active"
		batch.save(ignore_permissions=True)

		log = frappe.new_doc("Poultry Daily Log")
		log.log_date = nowdate()
		log.batch = batch.name
		log.water_consumption_liters = 200.0  # 200 Liters
		log.lighting_hours = 16.0

		# Flock entry: 10 dead from Heat Stress, 5 culled
		log.append(
			"flock_entries",
			{
				"shed": "Test Layer Shed",
				"batch": batch.name,
				"opening_birds": 1000,
				"dead": 10,
				"mortality_cause": "Heat Stress",
				"culled": 5,
				"closing_birds": 985,
			},
		)

		# Feed entry: 100 kg feed spent at $2.50/kg = $250.00
		log.append(
			"feed_entries",
			{
				"shed": "Test Layer Shed",
				"batch": batch.name,
				"feed_spent_kg": 100.0,
				"rate_per_kg": 2.50,
			},
		)

		# Egg entry: 800 good eggs, 50 double yolk, 20 broken, 10 waste = 880 total eggs
		log.append(
			"egg_entries",
			{
				"shed": "Test Layer Shed",
				"batch": batch.name,
				"good_eggs": 800,
				"double_yolk_eggs": 50,
				"broken_eggs": 20,
				"waste_eggs": 10,
			},
		)

		log.validate()

		# Verify Water per bird: 200 L * 1000 / 985 closing birds = 203.05 ml/bird
		self.assertAlmostEqual(flt(log.water_per_bird_ml), 203.05, places=1)

		# Verify Water : Feed ratio: 200 L / 100 kg = 2.00
		self.assertAlmostEqual(flt(log.water_feed_ratio), 2.0, places=2)

		# Verify HHEP % on egg row and parent: (880 total eggs / 1000 initial birds) * 100 = 88.0%
		self.assertEqual(flt(log.egg_entries[0].hhep_pct), 88.0)
		self.assertEqual(flt(log.hen_housed_production_pct), 88.0)

		# Verify Feed Cost per Egg: Total feed cost (100 * 2.50 = 250) / good eggs (800 + 50 = 850)
		# 250 / 850 = 0.29
		self.assertAlmostEqual(flt(log.feed_cost_per_egg), 0.29, places=2)

	def test_weight_based_live_bird_custom_fields(self):
		"""Test weight-based live bird fields exist on Sales Order Item."""
		so_meta = frappe.get_meta("Sales Order Item")
		self.assertTrue(so_meta.has_field("is_weight_based_live_bird_sale"))
		self.assertTrue(so_meta.has_field("gross_weight_kg"))
		self.assertTrue(so_meta.has_field("tare_weight_kg"))
		self.assertTrue(so_meta.has_field("net_weight_kg"))
		self.assertTrue(so_meta.has_field("birds_count"))
		self.assertTrue(so_meta.has_field("avg_bird_weight_kg"))

	def test_reports_execution(self):
		"""Test that all updated poultry reports execute cleanly with valid columns."""
		from ob_poultry.poultry.report.poultry_batch_analysis import poultry_batch_analysis
		from ob_poultry.poultry.report.poultry_batch_performance_review import (
			poultry_batch_performance_review,
		)
		from ob_poultry.poultry.report.poultry_bird_count_trend import poultry_bird_count_trend
		from ob_poultry.poultry.report.poultry_bodyweight_report import poultry_bodyweight_report
		from ob_poultry.poultry.report.poultry_chick_stock import poultry_chick_stock
		from ob_poultry.poultry.report.poultry_chick_summary import poultry_chick_summary
		from ob_poultry.poultry.report.poultry_egg_production_cost import poultry_egg_production_cost
		from ob_poultry.poultry.report.poultry_egg_production_report import poultry_egg_production_report
		from ob_poultry.poultry.report.poultry_empty_sheds import poultry_empty_sheds
		from ob_poultry.poultry.report.poultry_feed_consumption_report import (
			poultry_feed_consumption_report,
		)
		from ob_poultry.poultry.report.poultry_mortality_report import poultry_mortality_report
		from ob_poultry.poultry.report.poultry_net_egg_stock import poultry_net_egg_stock

		filters = {
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"as_of_date": nowdate(),
		}

		# 1. Egg Production Report
		cols, _ = poultry_egg_production_report.execute(filters)
		self.assertTrue(any(c["fieldname"] == "hhep_pct" for c in cols))
		self.assertTrue(any(c["fieldname"] == "feed_cost_per_egg" for c in cols))

		# 2. Mortality Report
		cols, _ = poultry_mortality_report.execute(filters)
		self.assertTrue(any(c["fieldname"] == "cause" for c in cols))
		self.assertTrue(any(c["fieldname"] == "mortality_pct" for c in cols))

		# 3. Batch Performance Review
		cols, _ = poultry_batch_performance_review.execute({})
		self.assertTrue(any(c["fieldname"] == "cumulative_ehh" for c in cols))
		self.assertTrue(any(c["fieldname"] == "avg_feed_cost_per_egg" for c in cols))
		self.assertTrue(any(c["fieldname"] == "housing_type" for c in cols))

		# 4. Batch Analysis
		cols, _ = poultry_batch_analysis.execute({})
		self.assertTrue(any(c["fieldname"] == "cumulative_ehh" for c in cols))
		self.assertTrue(any(c["fieldname"] == "avg_hhep_pct" for c in cols))

		# 5. Egg Production Cost
		cols, _ = poultry_egg_production_cost.execute(filters)
		self.assertTrue(any(c["fieldname"] == "cost_per_egg" for c in cols))
		self.assertTrue(any(c["fieldname"] == "hhep_pct" for c in cols))

		# 6. Net Egg Stock
		cols, _ = poultry_net_egg_stock.execute(filters)
		self.assertTrue(any(c["fieldname"] == "net_stock" for c in cols))
		self.assertTrue(any(c["fieldname"] == "cold_room_balance" for c in cols))

		# 7. Feed Consumption Report
		cols, _ = poultry_feed_consumption_report.execute(filters)
		self.assertTrue(any(c["fieldname"] == "water_feed_ratio" for c in cols))
		self.assertTrue(any(c["fieldname"] == "water_consumption_liters" for c in cols))

		# 8. Empty Sheds
		cols, _ = poultry_empty_sheds.execute()
		self.assertTrue(any(c["fieldname"] == "housing_type" for c in cols))

		# 9. Chick Stock & Summary
		cols, _ = poultry_chick_stock.execute({})
		self.assertTrue(any(c["fieldname"] == "hatched_egg" for c in cols))
		self.assertTrue(any(c["fieldname"] == "move_to_stock" for c in cols))

		cols, _ = poultry_chick_summary.execute({})
		self.assertTrue(any(c["fieldname"] == "total_move_to_stock" for c in cols))

		# 10. Bird Count Trend & Bodyweight
		batch = frappe.db.get_value("Poultry Batch", {}, "name")
		if batch:
			cols, _ = poultry_bird_count_trend.execute({"batch": batch})
			self.assertTrue(any(c["fieldname"] == "age_weeks" for c in cols))

			cols, _ = poultry_bodyweight_report.execute({"from_date": "2026-01-01", "to_date": "2026-12-31"})
			self.assertTrue(any(c["fieldname"] == "age_weeks" for c in cols))

	def test_batch_individual_weight_and_context(self):
		"""Test per-batch body weight in flock entries and get_shed_context benchmarks."""
		from ob_poultry.poultry.doctype.poultry_daily_log.poultry_daily_log import get_shed_context
		from ob_poultry.poultry.report.poultry_bodyweight_report import poultry_bodyweight_report

		# Create 17-week pullet batch
		batch = frappe.new_doc("Poultry Batch")
		batch.batch_name = "Test Weight Pullet Batch"
		batch.breed = "Test Layer Breed"
		batch.shed = "Test Layer Shed"
		batch.start_date = nowdate()
		batch.initial_bird_count = 500
		batch.current_bird_count = 500
		batch.status = "Active"
		batch.placement_age_weeks = 17
		batch.placement_age_days = 0
		batch.save(ignore_permissions=True)

		ctx = get_shed_context("Test Layer Shed", nowdate())
		self.assertIn("batches", ctx)
		b_item = next((b for b in ctx["batches"] if b["batch"] == batch.name), None)
		self.assertIsNotNone(b_item)
		self.assertEqual(b_item["effective_age_days"], 119)  # 17 * 7
		self.assertEqual(b_item["week_day"], "W17 D0")

		# Create Daily Log with record_weight enabled
		log = frappe.new_doc("Poultry Daily Log")
		log.log_date = nowdate()
		log.record_weight = 1
		log.append(
			"flock_entries",
			{
				"batch": batch.name,
				"shed": "Test Layer Shed",
				"opening_birds": 500,
				"dead": 0,
				"culled": 0,
				"average_body_weight_g": 1625.5,
			},
		)
		log.compute_flock_rollups()
		self.assertEqual(flt(log.average_body_weight_g), 1625.5)

		# When record_weight is 0, average_body_weight_g resets to 0.0
		log.record_weight = 0
		log.compute_flock_rollups()
		self.assertEqual(flt(log.average_body_weight_g), 0.0)

	def test_daily_egg_stock_and_sales_flow(self):
		"""Test automated egg receipt into Cold Room and deduction on egg sales."""
		from ob_poultry.setup import setup_default_egg_cold_room

		setup_default_egg_cold_room()

		wh = frappe.db.get_single_value("Poultry Settings", "default_egg_warehouse") or "Egg Cold Room - P"
		item = frappe.db.get_single_value("Poultry Settings", "default_egg_item") or "Table Egg"

		# Ensure shed has default_egg_warehouse set
		frappe.db.set_value("Poultry Shed", "Test Layer Shed", "default_egg_warehouse", wh)

		# Baseline Bin qty
		init_bin_qty = flt(
			frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh}, "actual_qty") or 0.0
		)

		# Create Batch
		batch = frappe.new_doc("Poultry Batch")
		batch.batch_name = "Test Cold Room Batch"
		batch.breed = "Test Layer Breed"
		batch.shed = "Test Layer Shed"
		batch.start_date = "2026-11-20"
		batch.initial_bird_count = 500
		batch.current_bird_count = 500
		batch.status = "Active"
		batch.save(ignore_permissions=True)

		# Remove any existing log for this test date
		test_date = "2026-11-20"
		existing_log = frappe.db.get_value("Poultry Daily Log", {"log_date": test_date}, "name")
		if existing_log:
			frappe.delete_doc("Poultry Daily Log", existing_log, force=1)

		# 1. Create Daily Log with 100 Good + 20 Double Yolk = 120 Table Eggs, and 30 Sold
		log = frappe.new_doc("Poultry Daily Log")
		log.log_date = test_date
		log.selected_shed = "Test Layer Shed"
		log.append(
			"egg_entries",
			{
				"shed": "Test Layer Shed",
				"batch": batch.name,
				"good_eggs": 100,
				"double_yolk_eggs": 20,
				"broken_eggs": 0,
				"waste_eggs": 0,
			},
		)
		log.append(
			"sales_entries",
			{
				"shed": "Test Layer Shed",
				"batch": batch.name,
				"good_eggs": 30,
				"table_egg_rate": 5.0,
			},
		)
		log.save(ignore_permissions=True)

		# Verify Receipt Stock Entry created and submitted
		self.assertTrue(log.egg_stock_entry)
		se_receipt = frappe.get_doc("Stock Entry", log.egg_stock_entry)
		self.assertEqual(se_receipt.docstatus, 1)
		self.assertEqual(se_receipt.stock_entry_type, "Material Receipt")
		self.assertEqual(flt(se_receipt.items[0].qty), 120.0)

		# Verify Sales Stock Entry created and submitted
		self.assertTrue(log.egg_sales_stock_entry)
		se_sales = frappe.get_doc("Stock Entry", log.egg_sales_stock_entry)
		self.assertEqual(se_sales.docstatus, 1)
		self.assertEqual(se_sales.stock_entry_type, "Material Issue")
		self.assertEqual(flt(se_sales.items[0].qty), 30.0)

		# Verify net Bin stock: init + 120 - 30 = init + 90
		curr_bin_qty = flt(frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh}, "actual_qty"))
		self.assertEqual(curr_bin_qty, init_bin_qty + 90.0)

		# 2. Update Daily Log egg production (change good_eggs to 150 -> 170 table eggs)
		log.egg_entries[0].good_eggs = 150
		log.save(ignore_permissions=True)

		new_bin_qty = flt(frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh}, "actual_qty"))
		self.assertEqual(new_bin_qty, init_bin_qty + 140.0)

		# 3. Cancel Stock Entries on log cancellation
		log.on_cancel()
		reloaded_receipt = frappe.get_doc("Stock Entry", log.egg_stock_entry)
		reloaded_sales = frappe.get_doc("Stock Entry", log.egg_sales_stock_entry)
		self.assertEqual(reloaded_receipt.docstatus, 2)
		self.assertEqual(reloaded_sales.docstatus, 2)

		cancelled_bin_qty = flt(
			frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh}, "actual_qty")
		)
		self.assertEqual(cancelled_bin_qty, init_bin_qty)
