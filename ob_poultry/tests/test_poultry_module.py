import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate


class TestPoultryModule(IntegrationTestCase):
	"""Covers docs/TASKS_AND_TEST_CASES.md Epics 0-9. Each test method maps to one epic; TC-IDs are kept as comments for traceability back to that file."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)
		if not frappe.db.exists("Stock Entry Type", "Material Receipt"):
			frappe.get_doc({"doctype": "Stock Entry Type", "name": "Material Receipt", "purpose": "Material Receipt"}).insert(ignore_permissions=True)
		if not frappe.db.exists("Stock Entry Type", "Material Issue"):
			frappe.get_doc({"doctype": "Stock Entry Type", "name": "Material Issue", "purpose": "Material Issue"}).insert(ignore_permissions=True)
		if not frappe.db.exists("UOM", "Kg"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Kg"}).insert(ignore_permissions=True)
		if not frappe.db.exists("Item Group", "All Item Groups"):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": "All Item Groups", "is_group": 1}).insert(ignore_permissions=True)
		if not frappe.db.exists("Company", "Test Poultry Co"):
			frappe.get_doc({
				"doctype": "Company", "company_name": "Test Poultry Co", "abbr": "TPC",
				"default_currency": "USD", "country": "United States",
			}).insert(ignore_permissions=True)

		cls.warehouse_name = frappe.db.get_value("Warehouse", {"company": "Test Poultry Co", "warehouse_name": "Stores"}, "name")

		for code in ["Test Starter Feed", "Test Maize", "Test Soya", "Test Premix", "Test Finished Feed"]:
			if not frappe.db.exists("Item", code):
				frappe.get_doc({"doctype": "Item", "item_code": code, "item_group": "All Item Groups", "stock_uom": "Kg", "is_stock_item": 1}).insert(ignore_permissions=True)

		receipt = frappe.get_doc({
			"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": "Test Poultry Co",
			"items": [{"item_code": "Test Starter Feed", "qty": 1000000, "t_warehouse": cls.warehouse_name, "basic_rate": 1, "set_basic_rate_manually": 1}],
		})
		receipt.insert(ignore_permissions=True)
		receipt.submit()

		cls.shed = frappe.get_doc({"doctype": "Poultry Shed", "shed_name": "Test Shed V1", "capacity": 100000}).insert(ignore_permissions=True)
		cls.breed = frappe.get_doc({"doctype": "Poultry Breed", "breed_name": "Test Breed V1", "breed_type": "Broiler"}).insert(ignore_permissions=True)
		cls.other_breed = frappe.get_doc({"doctype": "Poultry Breed", "breed_name": "Test Breed V1 Other", "breed_type": "Layer"}).insert(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		# ERPNext's Company controller commits internally while creating default warehouses/accounts,
		# which escapes IntegrationTestCase's transaction rollback, so it must be deleted explicitly.
		frappe.delete_doc("Company", "Test Poultry Co", force=1, ignore_permissions=True, ignore_missing=True)
		super().tearDownClass()

	def bin_qty(self, item_code):
		return frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": self.warehouse_name}, "actual_qty") or 0

	def test_epic0_regression(self):
		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 1000, "feed_warehouse": self.warehouse_name}).insert(ignore_permissions=True)
		self.assertEqual(batch.current_bird_count, 1000)  # TC-REG-01

		with self.assertRaises(frappe.ValidationError):  # TC-REG-02
			frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 999999}).insert(ignore_permissions=True)

		log1 = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -3), "mortality_details": [{"cause": "Disease", "count": 5}], "cull_count": 1}).insert(ignore_permissions=True)
		log1.submit()
		batch.reload()
		self.assertEqual(batch.current_bird_count, 994)  # TC-REG-03

		with self.assertRaises(frappe.ValidationError):  # TC-REG-04
			frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -3), "mortality_count": 2}).insert(ignore_permissions=True)

		log1.cancel()
		batch.reload()
		self.assertEqual(batch.current_bird_count, 1000)  # TC-REG-05

		with self.assertRaises(frappe.ValidationError):  # TC-REG-06
			frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -3), "mortality_details": [{"cause": "Disease", "count": 999999}]}).insert(ignore_permissions=True)

		log2 = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -2), "feed_item": "Test Starter Feed", "feed_consumed_kg": 25}).insert(ignore_permissions=True)
		before_qty = self.bin_qty("Test Starter Feed")
		log2.submit()
		self.assertTrue(log2.stock_entry)  # TC-REG-07
		self.assertEqual(before_qty - self.bin_qty("Test Starter Feed"), 25)  # TC-REG-07

		log2.cancel()
		self.assertEqual(self.bin_qty("Test Starter Feed"), before_qty)  # TC-REG-08

		formula = frappe.get_doc({
			"doctype": "Poultry Feed Formula", "feed_name": "Test Formula REG", "feed_item": "Test Finished Feed", "batch_size_kg": 100,
			"ingredients": [{"raw_material": "Test Maize", "quantity_kg": 60}, {"raw_material": "Test Soya", "quantity_kg": 40}],
		}).insert(ignore_permissions=True)
		self.assertTrue(formula.create_or_update_bom())  # TC-REG-09
		wo = frappe.get_doc("Work Order", formula.make_work_order(50))
		self.assertEqual(wo.qty, 50)  # TC-REG-09

	def test_epic1_mortality_causes(self):
		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 10}).insert(ignore_permissions=True)

		log1 = frappe.get_doc({
			"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -5),
			"mortality_details": [{"cause": "Disease", "count": 3}, {"cause": "Heat Stress", "count": 2}],
		}).insert(ignore_permissions=True)
		self.assertEqual(log1.mortality_count, 5)  # TC-MORT-01

		log2 = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -4)}).insert(ignore_permissions=True)
		self.assertEqual(log2.mortality_count, 0)  # TC-MORT-02

		with self.assertRaises(frappe.ValidationError):  # TC-MORT-03
			frappe.get_doc({
				"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -3),
				"mortality_details": [{"cause": "Disease", "count": 20}],
			}).insert(ignore_permissions=True)

	def test_epic2_egg_grading(self):
		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.other_breed.name, "start_date": nowdate(), "initial_bird_count": 1000}).insert(ignore_permissions=True)

		day1 = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -10), "egg_entries": [{"grade": "Table Egg", "production_count": 200}]})
		day1.insert(ignore_permissions=True)
		day1.submit()
		self.assertEqual(day1.egg_entries[0].opening_count, 0)  # TC-EGG-02

		day2 = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -9), "egg_entries": [{"grade": "Table Egg", "production_count": 150}]}).insert(ignore_permissions=True)
		self.assertEqual(day2.egg_entries[0].opening_count, 200)  # TC-EGG-01
		self.assertEqual(day2.egg_entries[0].closing_count, 350)  # TC-EGG-01

		day3 = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -8), "egg_entries": [
			{"grade": "Table Egg", "production_count": 100}, {"grade": "Jumbo Egg", "production_count": 50}, {"grade": "Waste Egg", "production_count": 10},
		]}).insert(ignore_permissions=True)
		self.assertEqual(day3.total_eggs_produced, 160)  # TC-EGG-03

		day4 = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -7), "egg_entries": [{"grade": "Table Egg", "production_count": 800}]}).insert(ignore_permissions=True)
		self.assertEqual(day4.hdep_percent, 80)  # TC-EGG-04, batch.current_bird_count is 1000

		zero_batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.other_breed.name, "start_date": nowdate(), "initial_bird_count": 0}).insert(ignore_permissions=True)
		zero_log = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": zero_batch.name, "log_date": nowdate(), "egg_entries": [{"grade": "Table Egg", "production_count": 5}]}).insert(ignore_permissions=True)
		self.assertEqual(zero_log.hdep_percent, 0)  # TC-EGG-05

	def test_epic3_benchmarks(self):
		bmk_breed = frappe.get_doc({"doctype": "Poultry Breed", "breed_name": "Test Benchmark Breed", "breed_type": "Broiler"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Poultry Benchmark", "breed": bmk_breed.name, "age_in_days": 10, "standard_body_weight_g": 250, "standard_feed_per_bird_g": 40, "standard_mortality_pct": 1}).insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):  # TC-BMK-01
			frappe.get_doc({"doctype": "Poultry Benchmark", "breed": bmk_breed.name, "age_in_days": 10, "standard_body_weight_g": 999}).insert(ignore_permissions=True)

		bmk_batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": bmk_breed.name, "start_date": add_days(nowdate(), -10), "initial_bird_count": 500}).insert(ignore_permissions=True)
		exact_log = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": bmk_batch.name, "log_date": nowdate(), "average_body_weight_g": 245}).insert(ignore_permissions=True)
		self.assertEqual(exact_log.std_body_weight_g, 250)  # TC-BMK-02

		bmk_breed2 = frappe.get_doc({"doctype": "Poultry Breed", "breed_name": "Test Benchmark Breed 2", "breed_type": "Broiler"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Poultry Benchmark", "breed": bmk_breed2.name, "age_in_days": 7, "standard_body_weight_g": 150}).insert(ignore_permissions=True)
		bmk_batch2 = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": bmk_breed2.name, "start_date": add_days(nowdate(), -9), "initial_bird_count": 500}).insert(ignore_permissions=True)
		nearest_log = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": bmk_batch2.name, "log_date": nowdate()}).insert(ignore_permissions=True)
		self.assertEqual(nearest_log.std_body_weight_g, 150)  # TC-BMK-03

		bmk_breed3 = frappe.get_doc({"doctype": "Poultry Breed", "breed_name": "Test Benchmark Breed No Data", "breed_type": "Broiler"}).insert(ignore_permissions=True)
		bmk_batch3 = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": bmk_breed3.name, "start_date": nowdate(), "initial_bird_count": 500}).insert(ignore_permissions=True)
		none_log = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": bmk_batch3.name, "log_date": nowdate()}).insert(ignore_permissions=True)
		self.assertFalse(none_log.std_body_weight_g)  # TC-BMK-04

	def test_epic4_fcr_cfcr(self):
		fresh_batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 500}).insert(ignore_permissions=True)
		self.assertEqual(fresh_batch.fcr, 0)  # TC-FCR-04
		self.assertEqual(fresh_batch.cfcr, 0)  # TC-FCR-04

		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 900, "feed_warehouse": self.warehouse_name}).insert(ignore_permissions=True)
		log1 = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -2), "feed_item": "Test Starter Feed", "feed_consumed_kg": 3240, "average_body_weight_g": 2000}).insert(ignore_permissions=True)
		log1.submit()
		batch.reload()
		self.assertEqual(batch.cumulative_feed_kg, 3240)  # TC-FCR-01
		self.assertAlmostEqual(batch.fcr, 1.8, places=3)  # TC-FCR-02

		log2 = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -1), "mortality_details": [{"cause": "Disease", "count": 10}], "average_body_weight_g": 2000}).insert(ignore_permissions=True)
		log2.submit()
		batch.reload()
		# The implemented formula folds mortality weight into CFCR's denominator only, so CFCR <= FCR
		# whenever there's mortality (the opposite of the original TASKS_AND_TEST_CASES.md guess).
		self.assertLessEqual(batch.cfcr, batch.fcr)  # TC-FCR-03
		self.assertNotEqual(batch.cfcr, batch.fcr)  # TC-FCR-03

	def test_epic5_vaccination_scheduling(self):
		vac_breed = frappe.get_doc({"doctype": "Poultry Breed", "breed_name": "Test Vaccine Breed", "breed_type": "Broiler"}).insert(ignore_permissions=True)
		frappe.get_doc({
			"doctype": "Poultry Vaccination Schedule Template", "template_name": "Test Vaccine Template", "breed": vac_breed.name,
			"items": [
				{"age_in_days": 0, "vaccine_name": "MD Live", "dose": "0.2cc", "method": "SubCutaneous"},
				{"age_in_days": 7, "vaccine_name": "ND Lasota", "dose": "Single", "method": "Eye Drop"},
				{"age_in_days": 14, "vaccine_name": "IBD", "dose": "Single", "method": "Drinking Water"},
			],
		}).insert(ignore_permissions=True)

		vac_batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": vac_breed.name, "start_date": nowdate(), "initial_bird_count": 500}).insert(ignore_permissions=True)
		due_rows = frappe.get_all("Poultry Vaccination Due", filters={"batch": vac_batch.name}, fields=["name", "age_in_days", "due_date", "status"], order_by="age_in_days")
		self.assertEqual(len(due_rows), 3)  # TC-VAC-01
		self.assertEqual(str(due_rows[1].due_date), add_days(nowdate(), 7))  # TC-VAC-01

		no_template_batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 500}).insert(ignore_permissions=True)
		self.assertEqual(frappe.db.count("Poultry Vaccination Due", {"batch": no_template_batch.name}), 0)  # TC-VAC-02

		record = frappe.get_doc({"doctype": "Poultry Vaccination Record", "batch": vac_batch.name, "due": due_rows[0].name, "vaccine_name": "MD Live", "date_given": nowdate()}).insert(ignore_permissions=True)
		due_after = frappe.db.get_value("Poultry Vaccination Due", due_rows[0].name, ["status", "vaccination_record"], as_dict=True)
		self.assertEqual(due_after.status, "Done")  # TC-VAC-03
		self.assertEqual(due_after.vaccination_record, record.name)  # TC-VAC-03

		adhoc = frappe.get_doc({"doctype": "Poultry Vaccination Record", "batch": vac_batch.name, "vaccine_name": "Ad Hoc Vaccine", "date_given": nowdate()}).insert(ignore_permissions=True)
		self.assertTrue(adhoc.name)  # TC-VAC-04
		self.assertEqual(frappe.db.get_value("Poultry Vaccination Due", due_rows[1].name, "status"), "Pending")  # TC-VAC-04

		with self.assertRaises(frappe.ValidationError):  # TC-VAC-05
			frappe.get_doc({"doctype": "Poultry Vaccination Record", "batch": vac_batch.name, "vaccine_name": "Bad Dates", "date_given": nowdate(), "next_due_date": add_days(nowdate(), -1)}).insert(ignore_permissions=True)

	def test_epic6_ingredient_categories(self):
		formula = frappe.get_doc({
			"doctype": "Poultry Feed Formula", "feed_name": "Test Formula CAT", "feed_item": "Test Finished Feed", "batch_size_kg": 100,
			"ingredients": [
				{"raw_material": "Test Maize", "quantity_kg": 60, "category": "Raw Material"},
				{"raw_material": "Test Soya", "quantity_kg": 30, "category": "Raw Material"},
				{"raw_material": "Test Premix", "quantity_kg": 2, "category": "Medicine"},
			],
		}).insert(ignore_permissions=True)
		self.assertEqual(formula.raw_material_total_kg, 90)  # TC-CAT-01
		self.assertEqual(formula.medicine_total_kg, 2)  # TC-CAT-01
		self.assertEqual(formula.ingredients[0].percentage, 60)  # TC-CAT-03
		self.assertEqual(formula.ingredients[2].percentage, 2)  # TC-CAT-03

		default_formula = frappe.get_doc({
			"doctype": "Poultry Feed Formula", "feed_name": "Test Formula CAT Default", "feed_item": "Test Finished Feed", "batch_size_kg": 100,
			"ingredients": [{"raw_material": "Test Maize", "quantity_kg": 50}],
		}).insert(ignore_permissions=True)
		self.assertEqual(default_formula.ingredients[0].category, "Raw Material")  # TC-CAT-02

	def test_epic7_feed_production(self):
		formula = frappe.get_doc({
			"doctype": "Poultry Feed Formula", "feed_name": "Test Formula PROD", "feed_item": "Test Finished Feed", "batch_size_kg": 100,
			"ingredients": [{"raw_material": "Test Maize", "quantity_kg": 100, "category": "Raw Material"}],
		}).insert(ignore_permissions=True)

		production = frappe.get_doc({"doctype": "Poultry Feed Production", "formula": formula.name, "planned_batches": 5}).insert(ignore_permissions=True)
		self.assertEqual(production.planned_qty_kg, 500)  # TC-PROD-01

		wo = frappe.get_doc("Work Order", production.create_work_order())
		self.assertEqual(wo.qty, 500)  # TC-PROD-02
		production.reload()
		self.assertTrue(production.work_order)  # TC-PROD-02

		production.actual_output_kg = 510
		production.save()
		self.assertEqual(production.yield_percent, 102)  # TC-PROD-03

		production2 = frappe.get_doc({"doctype": "Poultry Feed Production", "formula": formula.name, "planned_batches": 2}).insert(ignore_permissions=True)
		self.assertFalse(production2.yield_percent)  # TC-PROD-04

	def test_epic8_roles_permissions(self):
		test_email = "poultry.attendant.test@example.com"
		if not frappe.db.exists("User", test_email):
			user = frappe.get_doc({"doctype": "User", "email": test_email, "first_name": "Test Attendant", "send_welcome_email": 0})
			user.insert(ignore_permissions=True)
			user.add_roles("Poultry Attendant")

		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 200}).insert(ignore_permissions=True)

		frappe.set_user(test_email)
		try:
			frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": nowdate()}).insert()
			log_created = True
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(log_created)  # TC-ROLE-01

		frappe.set_user(test_email)
		with self.assertRaises(frappe.PermissionError):  # TC-ROLE-01
			frappe.get_doc("Poultry Batch", batch.name).close_batch()
		frappe.set_user("Administrator")

		frappe.set_user(test_email)
		with self.assertRaises(frappe.PermissionError):  # TC-ROLE-02
			frappe.get_doc("Poultry Shed", self.shed.name).save()
		frappe.set_user("Administrator")

	def test_epic9_closed_batch_guard(self):
		closed_batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 100}).insert(ignore_permissions=True)
		closed_batch.close_batch()
		with self.assertRaises(frappe.ValidationError):  # TC-CLOSE-01
			frappe.get_doc({"doctype": "Poultry Daily Log", "batch": closed_batch.name, "log_date": nowdate()}).insert(ignore_permissions=True)

		open_batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 100}).insert(ignore_permissions=True)
		open_log = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": open_batch.name, "log_date": nowdate()}).insert(ignore_permissions=True)
		self.assertTrue(open_log.name)  # TC-CLOSE-02

	# --- v2 (docs/ROADMAP.md "Later — v2") ---

	def test_v2_growing_charge_scheme(self):
		scheme = frappe.get_doc({
			"doctype": "Poultry Growing Charge Scheme", "scheme_name": "Test GC Scheme",
			"rates": [
				{"min_weight_g": 0, "max_weight_g": 1500, "rate_per_kg": 8},
				{"min_weight_g": 1500, "max_weight_g": 2500, "rate_per_kg": 10},
				{"min_weight_g": 2500, "rate_per_kg": 12},
			],
		}).insert(ignore_permissions=True)
		self.assertEqual(scheme.get_rate_for_weight(1000), 8)
		self.assertEqual(scheme.get_rate_for_weight(2000), 10)
		self.assertEqual(scheme.get_rate_for_weight(3000), 12)  # open-ended top bracket

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({
				"doctype": "Poultry Growing Charge Scheme", "scheme_name": "Test GC Scheme Bad",
				"rates": [{"min_weight_g": 1000, "max_weight_g": 500, "rate_per_kg": 5}],
			}).insert(ignore_permissions=True)

	def test_v2_contract_batch_and_growing_charge(self):
		farmer = frappe.get_doc({"doctype": "Poultry Farmer", "farmer_name": "Test Farmer", "branch": "Test Branch", "line": "Test Line"}).insert(ignore_permissions=True)
		scheme = frappe.get_doc({
			"doctype": "Poultry Growing Charge Scheme", "scheme_name": "Test GC Scheme 2",
			"rates": [{"min_weight_g": 0, "max_weight_g": 2500, "rate_per_kg": 10}, {"min_weight_g": 2500, "rate_per_kg": 12}],
		}).insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 500, "flock_source": "Contract"}).insert(ignore_permissions=True)

		batch = frappe.get_doc({
			"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(),
			"initial_bird_count": 500, "flock_source": "Contract", "farmer": farmer.name, "growing_charge_scheme": scheme.name,
		}).insert(ignore_permissions=True)
		log = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": nowdate(), "average_body_weight_g": 2000}).insert(ignore_permissions=True)
		log.submit()
		batch.reload()
		amount = batch.calculate_growing_charge()
		self.assertEqual(amount, 10000)  # 500 birds * 2.0kg * 10/kg
		batch.reload()
		self.assertEqual(batch.growing_charge_amount, 10000)

		owned_batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 100}).insert(ignore_permissions=True)
		self.assertEqual(owned_batch.flock_source, "Owned")

	def test_v2_hatchery_and_chick_transfer(self):
		hatchery = frappe.get_doc({"doctype": "Poultry Hatchery", "hatchery_name": "Test Hatchery", "capacity_eggs": 50000}).insert(ignore_permissions=True)
		hatch = frappe.get_doc({"doctype": "Poultry Hatch", "hatchery": hatchery.name, "schedule_date": nowdate(), "eggs_set": 10000, "standard_hatchability_pct": 82}).insert(ignore_permissions=True)
		self.assertEqual(hatch.estimated_chicks, 8200)

		hatch.actual_chicks = 8100
		hatch.save()

		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 100}).insert(ignore_permissions=True)
		batch2 = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 100}).insert(ignore_permissions=True)

		transfer1 = frappe.get_doc({"doctype": "Poultry Chick Transfer", "hatch": hatch.name, "batch": batch.name, "transfer_date": nowdate(), "quantity": 5000}).insert(ignore_permissions=True)
		transfer1.submit()

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Poultry Chick Transfer", "hatch": hatch.name, "batch": batch2.name, "transfer_date": nowdate(), "quantity": 4000}).insert(ignore_permissions=True)

		transfer2 = frappe.get_doc({"doctype": "Poultry Chick Transfer", "hatch": hatch.name, "batch": batch2.name, "transfer_date": nowdate(), "quantity": 3000}).insert(ignore_permissions=True)
		self.assertTrue(transfer2.name)

	def test_v2_feed_formula_nutrients_and_mortality_photo(self):
		formula = frappe.get_doc({
			"doctype": "Poultry Feed Formula", "feed_name": "Test Formula Nutrients", "feed_item": "Test Finished Feed", "batch_size_kg": 100,
			"ingredients": [{"raw_material": "Test Maize", "quantity_kg": 100}],
			"nutrients": [{"nutrient": "Crude Protein", "value": 21, "unit": "%"}, {"nutrient": "ME", "value": 3000, "unit": "Kcal/kg"}],
		}).insert(ignore_permissions=True)
		self.assertEqual(len(formula.nutrients), 2)

		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 100}).insert(ignore_permissions=True)
		log = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": nowdate(), "mortality_details": [{"cause": "Disease", "count": 1}]}).insert(ignore_permissions=True)
		self.assertTrue(hasattr(log.mortality_details[0], "photo"))

	# --- Daily Register Parity (docs/TASKS_AND_TEST_CASES.md Epics 11-19) ---

	def test_epic11_daily_mortality_pct(self):
		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 1000}).insert(ignore_permissions=True)
		log = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": nowdate(), "mortality_details": [{"cause": "Disease", "count": 50}]}).insert(ignore_permissions=True)
		self.assertEqual(log.daily_mortality_pct, 5)  # TC-DMP-01, 50/1000*100

		zero_batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 0}).insert(ignore_permissions=True)
		zero_log = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": zero_batch.name, "log_date": nowdate()}).insert(ignore_permissions=True)
		self.assertEqual(zero_log.daily_mortality_pct, 0)  # TC-DMP-02, safe at zero birds

	def test_epic12_double_yolk_grade_and_trays(self):
		frappe.get_single("Poultry Settings").db_set("eggs_per_tray", 30)
		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 500}).insert(ignore_permissions=True)
		log = frappe.get_doc({
			"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": nowdate(),
			"egg_entries": [{"grade": "Double Yolk", "production_count": 60}, {"grade": "Dirty Egg", "production_count": 15}],
		}).insert(ignore_permissions=True)
		self.assertEqual(log.egg_entries[0].trays, 2)  # TC-TRAY-01, 60/30
		self.assertEqual(log.egg_entries[1].trays, 0.5)  # TC-TRAY-01, 15/30

	def test_epic13_feed_uom_conversion(self):
		if not frappe.db.exists("UOM", "Bag"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Bag"}).insert(ignore_permissions=True)
		item = frappe.get_doc("Item", "Test Starter Feed")
		if not any(row.uom == "Bag" for row in item.uoms):
			item.append("uoms", {"uom": "Bag", "conversion_factor": 50})
			item.save(ignore_permissions=True)

		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 500, "feed_warehouse": self.warehouse_name}).insert(ignore_permissions=True)
		log = frappe.get_doc({
			"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": nowdate(),
			"feed_item": "Test Starter Feed", "feed_uom": "Bag", "feed_qty": 2,
		}).insert(ignore_permissions=True)
		self.assertEqual(log.feed_consumed_kg, 100)  # TC-BAG-01, 2 bags * 50kg/bag

		direct_log = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": add_days(nowdate(), -1), "feed_item": "Test Starter Feed", "feed_consumed_kg": 30}).insert(ignore_permissions=True)
		self.assertEqual(direct_log.feed_consumed_kg, 30)  # TC-BAG-02, unchanged when feed_uom left blank

	def test_epic16_daily_expenses(self):
		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 200}).insert(ignore_permissions=True)
		log = frappe.get_doc({
			"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": nowdate(),
			"expenses": [{"description": "Labour", "amount": 500}, {"description": "Electricity", "amount": 150}],
		}).insert(ignore_permissions=True)
		self.assertEqual(log.total_expenses, 650)  # TC-EXP-01

	def test_epic17_egg_sale(self):
		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 500}).insert(ignore_permissions=True)
		log = frappe.get_doc({"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": nowdate(), "egg_entries": [{"grade": "Table Egg", "production_count": 100}]}).insert(ignore_permissions=True)
		log.submit()

		if not frappe.db.exists("Customer", "Test Egg Buyer"):
			frappe.get_doc({"doctype": "Customer", "customer_name": "Test Egg Buyer"}).insert(ignore_permissions=True)

		sale = frappe.get_doc({
			"doctype": "Poultry Egg Sale", "batch": batch.name, "customer": "Test Egg Buyer", "sale_date": nowdate(),
			"items": [{"grade": "Table Egg", "quantity": 30, "rate": 5}],
		}).insert(ignore_permissions=True)
		self.assertEqual(sale.total_amount, 150)  # TC-SALE-01
		sale.submit()  # so the next sale's stock check (which only counts submitted sales) sees it

		with self.assertRaises(frappe.ValidationError):  # TC-SALE-02, only 70 left in stock
			frappe.get_doc({
				"doctype": "Poultry Egg Sale", "batch": batch.name, "customer": "Test Egg Buyer", "sale_date": nowdate(),
				"items": [{"grade": "Table Egg", "quantity": 71, "rate": 5}],
			}).insert(ignore_permissions=True)

	def test_epic18_shed_default_feed_warehouse(self):
		shed_with_default = frappe.get_doc({"doctype": "Poultry Shed", "shed_name": "Test Shed Default WH", "capacity": 5000, "default_feed_warehouse": self.warehouse_name}).insert(ignore_permissions=True)
		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": shed_with_default.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 100}).insert(ignore_permissions=True)
		self.assertEqual(batch.feed_warehouse, self.warehouse_name)  # TC-SHEDWH-01

		explicit_batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": shed_with_default.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 100, "feed_warehouse": None}).insert(ignore_permissions=True)
		self.assertTrue(explicit_batch.feed_warehouse)  # TC-SHEDWH-01, defaulted rather than left blank

	def test_epic19_feed_per_bird_and_damage_pct(self):
		batch = frappe.get_doc({"doctype": "Poultry Batch", "shed": self.shed.name, "breed": self.breed.name, "start_date": nowdate(), "initial_bird_count": 100}).insert(ignore_permissions=True)
		log = frappe.get_doc({
			"doctype": "Poultry Daily Log", "batch": batch.name, "log_date": nowdate(), "feed_item": "Test Starter Feed", "feed_consumed_kg": 12,
			"egg_entries": [{"grade": "Table Egg", "production_count": 80}, {"grade": "Dirty Egg", "production_count": 20}],
		}).insert(ignore_permissions=True)
		self.assertEqual(log.feed_per_bird_g, 120)  # TC-DASH-01, 12kg*1000/100 birds
		self.assertEqual(log.damage_pct, 20)  # TC-DASH-02, 20 dirty / 100 total * 100
