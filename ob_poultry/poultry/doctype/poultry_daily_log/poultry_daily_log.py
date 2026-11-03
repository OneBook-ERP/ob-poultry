import frappe
from erpnext.stock.get_item_details import get_conversion_factor
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, date_diff, flt, getdate, nowdate


class PoultryDailyLog(Document):
	def onload(self):
		if not self.shed_entries:
			self.populate_shed_entries()
		self.cleanup_mock_data_if_needed()

	def cleanup_mock_data_if_needed(self):
		# Clear mock data from PDL-2026-00006 in 1st three tables while preserving fetched data
		if self.name == "PDL-2026-00006":
			try:
				frappe.db.sql(
					"""
					UPDATE `tabPoultry Daily Log Egg Entry`
					SET good_eggs=0, double_yolk_eggs=0, broken_eggs=0, waste_eggs=0,
						total_eggs=0, broken_egg_pct=0, egg_production_pct=0,
						trays=0, eggs_left=0, tray_summary='0 Trays, 0 Eggs'
					WHERE parent = %s
				""",
					(self.name,),
				)

				frappe.db.sql(
					"""
					UPDATE `tabPoultry Daily Log Feed Entry`
					SET feed_spent_kg=0, feed_spent_g_per_bird=0, total_feed_cost=0,
						currently_available_kg=opening_stock_kg
					WHERE parent = %s
				""",
					(self.name,),
				)

				frappe.db.sql(
					"""
					UPDATE `tabPoultry Daily Log Flock Entry`
					SET dead=0, culled=0, closing_birds=opening_birds
					WHERE parent = %s
				""",
					(self.name,),
				)

				frappe.db.sql(
					"""
					UPDATE `tabPoultry Daily Log`
					SET total_eggs_produced=0, total_feed_consumed_kg=0, feed_consumed_kg=0,
						total_feed_cost=0, total_mortality=0, mortality_count=0,
						total_culled=0, cull_count=0
					WHERE name = %s
				""",
					(self.name,),
				)
				frappe.db.commit()

				# Also clear in-memory child rows for the active form session
				for row in self.egg_entries:
					row.good_eggs = 0
					row.double_yolk_eggs = 0
					row.broken_eggs = 0
					row.waste_eggs = 0
					row.total_eggs = 0
					row.broken_egg_pct = 0.0
					row.egg_production_pct = 0.0
					row.trays = 0
					row.eggs_left = 0
					row.tray_summary = "0 Trays, 0 Eggs"

				for row in self.feed_entries:
					row.feed_spent_kg = 0.0
					row.feed_spent_g_per_bird = 0.0
					row.total_feed_cost = 0.0
					row.currently_available_kg = flt(row.opening_stock_kg)

				for row in self.flock_entries:
					row.dead = 0
					row.culled = 0
					row.closing_birds = cint(row.opening_birds)

				self.total_eggs_produced = 0
				self.total_feed_consumed_kg = 0.0
				self.feed_consumed_kg = 0.0
				self.total_feed_cost = 0.0
				self.total_mortality = 0
				self.mortality_count = 0
				self.total_culled = 0
				self.cull_count = 0
			except Exception:
				pass

	def before_insert(self):
		if not self.shed_entries:
			self.populate_shed_entries()

	def populate_shed_entries(self):
		active_sheds = get_active_sheds()
		current_sheds = {s.shed for s in self.shed_entries if s.shed}
		for s in active_sheds:
			if s["name"] not in current_sheds:
				self.append(
					"shed_entries",
					{
						"shed": s["name"],
						"batches_count": s["active_batches_count"],
						"total_birds": s["total_birds"],
						"breed": s["breeds"] or "-",
					},
				)

	def validate(self):
		if not self.log_date:
			self.log_date = nowdate()

		if not self.shed_entries:
			self.populate_shed_entries()

		self.validate_unique_daily_log()
		self.compute_day_of_week()
		self.compute_flock_rollups()
		self.compute_egg_rollups()
		self.compute_feed_rollups()
		self.compute_sales_rollups()

		# Support legacy mortality_details if flock_entries not present
		if self.get("mortality_details") and not self.flock_entries:
			self.mortality_count = sum(
				cint(r.get("count") or getattr(r, "count", 0)) for r in self.mortality_details
			)
			self.total_mortality = self.mortality_count
			self.total_culled = cint(self.cull_count)
		elif self.flock_entries:
			self.mortality_count = self.total_mortality
			self.cull_count = self.total_culled
		else:
			self.mortality_count = cint(self.mortality_count)
			self.cull_count = cint(self.cull_count)
			self.total_mortality = self.mortality_count
			self.total_culled = self.cull_count

		# Support legacy feed_consumed_kg if feed_entries not present
		if not self.feed_entries and self.feed_consumed_kg:
			self.total_feed_consumed_kg = flt(self.feed_consumed_kg)
		elif self.feed_entries:
			self.feed_consumed_kg = self.total_feed_consumed_kg
		else:
			self.feed_consumed_kg = flt(self.feed_consumed_kg)
			self.total_feed_consumed_kg = self.feed_consumed_kg

		self.apply_feed_uom_conversion()

		if self.get("batch"):
			self.validate_bird_count()
			self.compute_daily_mortality_pct()
			self.apply_benchmarks()

	def apply_feed_uom_conversion(self):
		if not (self.get("feed_uom") and self.get("feed_qty")):
			return
		if not self.get("feed_item"):
			frappe.throw(_("Set a Feed Item before entering Feed Qty in an alternate unit"))
		conversion_factor = flt(get_conversion_factor(self.feed_item, self.feed_uom).get("conversion_factor"))
		if not conversion_factor:
			frappe.throw(
				_("No UOM conversion factor found for {0} and {1}").format(self.feed_item, self.feed_uom)
			)
		self.feed_consumed_kg = round(flt(self.feed_qty) * conversion_factor, 3)
		self.total_feed_consumed_kg = self.feed_consumed_kg

	def compute_daily_mortality_pct(self):
		if self.batch_doc and self.batch_doc.current_bird_count:
			self.daily_mortality_pct = round(
				(flt(self.mortality_count) / self.batch_doc.current_bird_count * 100), 2
			)
		else:
			self.daily_mortality_pct = 0.0

	def on_update(self):
		self.update_batch_flocks()
		self.issue_feed_stock()
		self.update_bin_stock()

	def update_bin_stock(self):
		"""Update stock in Bin from daily log feed entries so warehouse balance is up to date."""
		default_feed_item = frappe.db.get_value("Poultry Settings", None, "default_feed_item")
		for row in self.feed_entries:
			if not row.warehouse:
				continue
			feed_item = row.feed_item or default_feed_item
			if not feed_item:
				feed_item = frappe.db.get_value("Item", {"is_stock_item": 1}, "name")

			if feed_item and row.warehouse:
				avail_qty = flt(row.currently_available_kg)
				bin_name = frappe.db.get_value(
					"Bin", {"item_code": feed_item, "warehouse": row.warehouse}, "name"
				)
				if bin_name:
					frappe.db.set_value("Bin", bin_name, "actual_qty", avail_qty)
				else:
					b = frappe.new_doc("Bin")
					b.item_code = feed_item
					b.warehouse = row.warehouse
					b.actual_qty = avail_qty
					b.valuation_rate = flt(row.rate_per_kg)
					b.insert(ignore_permissions=True)

	def validate_unique_daily_log(self):
		filters = {"log_date": self.log_date}
		if not self.is_new() and self.name:
			filters["name"] = ("!=", self.name)
		existing = frappe.db.get_value(
			"Poultry Daily Log",
			filters,
			"name",
		)
		if existing:
			frappe.throw(
				_(
					"A Poultry Daily Log already exists for date {0} ({1}). Only one log is allowed per day."
				).format(self.log_date, existing)
			)

	def compute_day_of_week(self):
		if self.log_date:
			dt = getdate(self.log_date)
			self.day_of_week = dt.strftime("%A")

	def compute_flock_rollups(self):
		total_dead = 0
		total_culls = 0
		for row in self.flock_entries:
			row.closing_birds = max(0, cint(row.opening_birds) - cint(row.dead) - cint(row.culled))
			total_dead += cint(row.dead)
			total_culls += cint(row.culled)

		if not self.flock_entries and self.get("mortality_details"):
			total_dead = sum(cint(r.count) for r in self.mortality_details)

		self.total_mortality = total_dead
		self.total_culled = total_culls

	@property
	def batch_doc(self):
		if not hasattr(self, "_batch_doc"):
			self._batch_doc = frappe.get_doc("Poultry Batch", self.batch) if self.get("batch") else None
		return self._batch_doc

	def validate_bird_count(self):
		if not self.get("batch"):
			return
		batch = self.batch_doc
		if not batch:
			return
		removed_elsewhere = (
			frappe.db.sql(
				"""
			select sum(mortality_count) + sum(cull_count) as removed
			from `tabPoultry Daily Log`
			where batch = %s and docstatus = 1 and name != %s
			""",
				(self.batch, self.name or ""),
				as_dict=True,
			)[0].removed
			or 0
		)
		transfer_reduction = 0
		if frappe.db.table_exists("Poultry Batch Shed Transfer"):
			transfer_reduction = (
				frappe.db.sql(
					"""
				select sum(reduction)
				from `tabPoultry Batch Shed Transfer`
				where parent = %s
				""",
					self.batch,
				)[0][0]
				or 0
			)
		total_removed = (
			removed_elsewhere + transfer_reduction + (self.mortality_count or 0) + (self.cull_count or 0)
		)
		if total_removed > batch.initial_bird_count:
			frappe.throw(
				_("Total removed birds ({0}) would exceed the initial bird count ({1}) for batch {2}").format(
					total_removed, batch.initial_bird_count, batch.name
				)
			)

	def compute_egg_rollups(self):
		# Map opening birds by batch from flock_entries for accurate production %
		batch_birds = {row.batch: cint(row.opening_birds) for row in self.flock_entries if row.batch}

		total_produced = 0
		for row in self.egg_entries:
			row.total_eggs = (
				cint(row.good_eggs)
				+ cint(row.double_yolk_eggs)
				+ cint(row.broken_eggs)
				+ cint(row.waste_eggs)
			)
			total_produced += row.total_eggs

			# Calculate Broken %
			if row.total_eggs > 0:
				row.broken_egg_pct = round((cint(row.broken_eggs) / row.total_eggs) * 100, 2)
			else:
				row.broken_egg_pct = 0.0

			# Calculate Production %
			birds = batch_birds.get(row.batch)
			if not birds and row.batch:
				birds = cint(frappe.db.get_value("Poultry Batch", row.batch, "current_bird_count"))
			if birds and birds > 0:
				row.egg_production_pct = round((row.total_eggs / birds) * 100, 2)
			else:
				row.egg_production_pct = 0.0

			# Trays (30 eggs/tray) and Left
			trays = row.total_eggs // 30
			left = row.total_eggs % 30
			row.trays = trays
			row.eggs_left = left
			row.tray_summary = f"{trays} Trays, {left} Eggs"

		self.total_eggs_produced = total_produced

	def compute_feed_rollups(self):
		batch_birds = {row.batch: cint(row.opening_birds) for row in self.flock_entries if row.batch}

		total_consumed = 0.0
		total_cost = 0.0
		for row in self.feed_entries:
			row.feed_spent_kg = flt(row.feed_spent_kg)
			total_consumed += row.feed_spent_kg

			# Grams per bird
			birds = batch_birds.get(row.batch)
			if not birds and row.batch:
				birds = cint(frappe.db.get_value("Poultry Batch", row.batch, "current_bird_count"))
			if birds and birds > 0:
				row.feed_spent_g_per_bird = round((row.feed_spent_kg * 1000.0) / birds, 2)
			else:
				row.feed_spent_g_per_bird = 0.0

			# Currently available stock
			row.currently_available_kg = max(0.0, flt(row.opening_stock_kg) - row.feed_spent_kg)

			# Cost calculation
			row.total_feed_cost = round(row.feed_spent_kg * flt(row.rate_per_kg), 2)
			total_cost += row.total_feed_cost

		self.total_feed_consumed_kg = total_consumed
		self.total_feed_cost = total_cost

	def compute_sales_rollups(self):
		total_sales = 0.0
		for row in self.sales_entries:
			table_rate = flt(row.table_egg_rate) or flt(row.get("rate"))
			broken_rate = flt(row.broken_egg_rate)
			row.table_egg_rate = table_rate
			row.table_egg_amount = round(cint(row.good_eggs) * table_rate, 2)
			row.broken_egg_amount = round(cint(row.broken_eggs) * broken_rate, 2)
			row.total_amount = round(row.table_egg_amount + row.broken_egg_amount, 2)
			total_sales += row.total_amount

		self.total_sales_amount = total_sales

	def apply_benchmarks(self):
		if not self.get("batch"):
			return
		batch = self.batch_doc
		if not batch or not getattr(batch, "breed", None):
			return
		age_in_days = date_diff(self.log_date, batch.start_date)
		benchmark = get_benchmark_for_age(batch.breed, age_in_days)
		if not benchmark:
			self.std_mortality_pct = None
			self.std_feed_per_bird_g = None
			self.std_body_weight_g = None
			self.std_hdep_pct = None
			return
		self.std_mortality_pct = benchmark.get("standard_mortality_pct")
		self.std_feed_per_bird_g = benchmark.get("standard_feed_per_bird_g")
		self.std_body_weight_g = benchmark.get("standard_body_weight_g")
		self.std_hdep_pct = benchmark.get("standard_hdep_pct")

	def on_submit(self):
		self.update_batch_flocks()
		self.issue_feed_stock()
		self.update_bin_stock()
		if self.get("batch"):
			self.create_feed_stock_entry()
			if self.batch_doc and hasattr(self.batch_doc, "recalculate_performance"):
				self.batch_doc.recalculate_performance()

	def on_cancel(self):
		if self.get("stock_entry"):
			stock_entry = frappe.get_doc("Stock Entry", self.stock_entry)
			if stock_entry.docstatus == 1:
				stock_entry.cancel()
		if self.get("batch") and self.batch_doc and hasattr(self.batch_doc, "recalculate_performance"):
			self.batch_doc.recalculate_performance()

	def create_feed_stock_entry(self):
		if not self.get("feed_consumed_kg"):
			return
		if not self.get("feed_item"):
			frappe.throw(_("Set a Feed Item to log feed consumption"))
		batch = self.batch_doc
		if not batch or not getattr(batch, "feed_warehouse", None):
			frappe.throw(
				_("Set a Feed Warehouse on Poultry Batch {0} before logging feed consumption").format(
					batch.name if batch else ""
				)
			)
		stock_entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Issue",
				"company": frappe.db.get_value("Warehouse", batch.feed_warehouse, "company"),
				"items": [
					{
						"item_code": self.feed_item,
						"s_warehouse": batch.feed_warehouse,
						"qty": self.feed_consumed_kg,
						"uom": frappe.db.get_value("Item", self.feed_item, "stock_uom"),
					}
				],
			}
		)
		stock_entry.insert(ignore_permissions=True)
		stock_entry.submit()
		self.stock_entry = stock_entry.name

	def update_batch_flocks(self):
		for row in self.flock_entries:
			if not row.batch:
				continue
			batch_doc = frappe.get_doc("Poultry Batch", row.batch)
			batch_doc.current_bird_count = max(0, cint(row.closing_birds))
			batch_doc.total_mortality = cint(batch_doc.total_mortality) + cint(row.dead)
			batch_doc.save(ignore_permissions=True)
		if (
			not self.flock_entries
			and self.get("batch")
			and hasattr(self.batch_doc, "recalculate_performance")
		):
			self.batch_doc.recalculate_performance()

	def issue_feed_stock(self):
		for row in self.feed_entries:
			if not (row.feed_spent_kg > 0 and row.warehouse):
				continue
			# If feed_item is set or configured in settings, record consumption
			feed_item = row.feed_item or frappe.db.get_value("Poultry Settings", None, "default_feed_item")
			if not feed_item:
				continue

			# Update cumulative feed on batch
			if row.batch:
				frappe.db.set_value(
					"Poultry Batch",
					row.batch,
					"cumulative_feed_kg",
					flt(frappe.db.get_value("Poultry Batch", row.batch, "cumulative_feed_kg"))
					+ row.feed_spent_kg,
				)
		if not self.feed_entries and self.get("batch") and self.get("feed_consumed_kg"):
			current_feed = flt(frappe.db.get_value("Poultry Batch", self.batch, "cumulative_feed_kg"))
			frappe.db.set_value(
				"Poultry Batch", self.batch, "cumulative_feed_kg", current_feed + flt(self.feed_consumed_kg)
			)


@frappe.whitelist()
def get_active_sheds():
	"""Returns all active sheds with summary of flock counts."""
	sheds = frappe.get_all(
		"Poultry Shed",
		filters={"is_active": 1},
		fields=["name", "shed_name", "capacity", "default_feed_warehouse"],
		order_by="shed_name asc",
	)

	for shed in sheds:
		batches = frappe.get_all(
			"Poultry Batch",
			filters={"shed": shed.name, "status": "Active"},
			fields=["name", "current_bird_count", "breed"],
		)
		shed["active_batches_count"] = len(batches)
		shed["total_birds"] = sum(cint(b.current_bird_count) for b in batches)
		shed["breeds"] = ", ".join(sorted(list({b.breed for b in batches if b.breed})))[:130]

	return sheds


def get_batch_opening_figures(batch, log_dt, current_birds_fallback=0):
	"""
	Calculates opening egg stock and opening live bird count for a batch on log_dt.
	- Opening Birds: Latest previous daily log closing_birds, or initial bird count if 1st time.
	- Opening Eggs: Latest previous (in_stock + total_eggs - total_eggs_sold), or 0 if 1st time.
	"""
	pdl = frappe.qb.DocType("Poultry Daily Log")
	flock_entry = frappe.qb.DocType("Poultry Daily Log Flock Entry")
	egg_entry = frappe.qb.DocType("Poultry Daily Log Egg Entry")
	sales_entry = frappe.qb.DocType("Poultry Daily Log Sales Entry")

	# 1. Opening Birds from latest preceding register
	flock_query = (
		frappe.qb.from_(flock_entry)
		.join(pdl)
		.on(pdl.name == flock_entry.parent)
		.select(flock_entry.closing_birds)
		.where(flock_entry.batch == batch)
		.where(pdl.log_date < log_dt)
		.where(pdl.docstatus < 2)
		.orderby(pdl.log_date, order=frappe.qb.desc)
		.orderby(pdl.creation, order=frappe.qb.desc)
		.limit(1)
	)
	flock_res = flock_query.run(as_dict=True)
	if flock_res and flock_res[0].closing_birds is not None:
		opening_birds = cint(flock_res[0].closing_birds)
	else:
		opening_birds = cint(current_birds_fallback) or cint(
			frappe.db.get_value("Poultry Batch", batch, "initial_bird_count")
		)

	# 2. Opening Eggs from latest preceding register
	egg_query = (
		frappe.qb.from_(egg_entry)
		.join(pdl)
		.on(pdl.name == egg_entry.parent)
		.select(egg_entry.in_stock, egg_entry.total_eggs, pdl.name.as_("parent_name"))
		.where(egg_entry.batch == batch)
		.where(pdl.log_date < log_dt)
		.where(pdl.docstatus < 2)
		.orderby(pdl.log_date, order=frappe.qb.desc)
		.orderby(pdl.creation, order=frappe.qb.desc)
		.limit(1)
	)
	egg_res = egg_query.run(as_dict=True)
	if egg_res:
		prev_in_stock = cint(egg_res[0].in_stock)
		prev_total = cint(egg_res[0].total_eggs)
		parent_name = egg_res[0].parent_name

		# Get total eggs sold for this batch in that previous log
		sales_query = (
			frappe.qb.from_(sales_entry)
			.select(sales_entry.good_eggs, sales_entry.double_yolk_eggs, sales_entry.broken_eggs)
			.where(sales_entry.parent == parent_name)
			.where(sales_entry.batch == batch)
		)
		sales_res = sales_query.run(as_dict=True)
		total_sold = sum(
			cint(s.good_eggs) + cint(s.double_yolk_eggs) + cint(s.broken_eggs) for s in sales_res
		)

		opening_eggs = max(0, (prev_in_stock + prev_total) - total_sold)
	else:
		opening_eggs = 0

	return opening_birds, opening_eggs


def get_benchmark_for_age(breed, age_in_days, breed_type=None):
	if not breed and not breed_type:
		return {}
	benchmark = {}
	if breed and frappe.db.table_exists("Poultry Breed Benchmark"):
		all_rows = frappe.db.sql(
			"""
			select standard_mortality_pct, standard_feed_per_bird_g, standard_body_weight_g, standard_fcr, standard_hdep_pct,
			       day_start, day_end, age_in_days, from_day, to_day
			from `tabPoultry Breed Benchmark`
			where parent = %s and parenttype = 'Poultry Breed'
			order by idx asc, coalesce(day_start, from_day) asc
			""",
			(breed,),
			as_dict=True,
		)
		for r in all_rows:
			if r.day_start is None and r.get("from_day") is not None:
				r.day_start = r.get("from_day")
			if r.day_end is None and r.get("to_day") is not None:
				r.day_end = r.get("to_day")
		rows = [
			r
			for r in all_rows
			if any(
				(r.get(f) or 0) > 0
				for f in (
					"standard_mortality_pct",
					"standard_feed_per_bird_g",
					"standard_body_weight_g",
					"standard_fcr",
					"standard_hdep_pct",
				)
			)
		]
		if rows:
			# Match exact day interval
			exact = [
				r
				for r in rows
				if (
					r.day_start is not None
					and r.day_end is not None
					and r.day_start <= age_in_days <= r.day_end
				)
			]
			if exact:
				benchmark = exact[-1]
			elif rows[0].day_start is not None and age_in_days <= rows[0].day_start:
				# Day 0 or young flock before first interval
				benchmark = rows[0]
			else:
				# Check if rows are entered by week number (e.g. 1, 2, 3...)
				batch_week_num = (age_in_days // 7) + 1
				week_match = [
					r
					for r in rows
					if (
						r.day_start is not None
						and r.day_end is not None
						and r.day_start <= batch_week_num <= r.day_end
					)
				]
				if week_match:
					benchmark = week_match[-1]
				else:
					earlier = [
						r
						for r in rows
						if (r.day_start is not None and r.day_start <= age_in_days)
						or (r.day_end is not None and r.day_end <= age_in_days)
					]
					if earlier:
						benchmark = earlier[-1]
					else:
						benchmark = rows[-1]

	# Fallback to standard built-in defaults by breed_type if custom benchmarks are not defined
	if not benchmark:
		if not breed_type and breed:
			breed_type = frappe.db.get_value("Poultry Breed", breed, "breed_type")
		if breed_type:
			from ob_poultry.poultry.doctype.poultry_breed.poultry_breed import get_default_benchmarks

			defaults = get_default_benchmarks(breed_type) or []
			if defaults:
				exact = [
					r
					for r in defaults
					if r.get("day_start") is not None
					and r.get("day_end") is not None
					and r["day_start"] <= age_in_days <= r["day_end"]
				]
				if exact:
					benchmark = exact[-1]
				elif age_in_days <= defaults[0].get("day_start", 0):
					benchmark = defaults[0]
				else:
					benchmark = defaults[-1]

	if not benchmark and frappe.db.table_exists("Poultry Benchmark"):
		legacy = frappe.db.sql(
			"""
			select standard_mortality_pct, standard_feed_per_bird_g, standard_body_weight_g
			from `tabPoultry Benchmark`
			where breed = %s and age_in_days <= %s
			order by age_in_days desc
			limit 1
			""",
			(breed, age_in_days),
			as_dict=True,
		)
		if legacy:
			benchmark = legacy[0]
	return benchmark or {}


@frappe.whitelist()
def get_shed_context(shed, log_date=None):
	"""Returns active batches and prefilled values for a given shed."""
	if not log_date:
		log_date = nowdate()

	log_dt = getdate(log_date)
	day_of_week = log_dt.strftime("%A")

	shed_doc = frappe.get_doc("Poultry Shed", shed)

	batch_fields = [
		"name",
		"breed",
		"breed_type",
		"start_date",
		"current_bird_count",
		"initial_bird_count",
		"feed_warehouse",
		"male_bird_count",
		"female_bird_count",
	]

	batches = frappe.get_all(
		"Poultry Batch",
		filters={"shed": shed, "status": "Active"},
		fields=batch_fields,
		order_by="name asc",
	)

	# Determine Breed and Sex
	breed = ""
	sex = "Mixed"
	if batches:
		breed = batches[0].breed or ""
		male = sum(cint(b.male_bird_count) for b in batches)
		female = sum(cint(b.female_bird_count) for b in batches)
		if female > 0 and male == 0:
			sex = "Female"
		elif male > 0 and female == 0:
			sex = "Male"
		elif female > 0 and male > 0:
			sex = "Mixed"
		elif batches[0].breed_type == "Layer":
			sex = "Female"

	batch_list = []
	shed_benchmark = None
	for idx, b in enumerate(batches):
		# Calculate Week / Day from batch start_date
		start_dt = getdate(b.start_date)
		days_elapsed = max(0, date_diff(log_dt, start_dt))
		weeks = days_elapsed // 7
		day_rem = days_elapsed % 7
		week_day_str = f"W{weeks} D{day_rem}"

		batch_breed = b.breed or breed
		bmk = get_benchmark_for_age(batch_breed, days_elapsed, b.breed_type)
		if not shed_benchmark and bmk:
			shed_benchmark = bmk

		# Warehouse prepopulation
		warehouse = b.feed_warehouse or shed_doc.default_feed_warehouse or ""

		# Opening stock balance and valuation rate
		stock_qty = 0.0
		rate_per_kg = 0.0
		feed_item = frappe.db.get_value("Poultry Settings", None, "default_feed_item") or ""

		if warehouse and feed_item:
			stock_qty = flt(
				frappe.db.get_value(
					"Bin",
					{"item_code": feed_item, "warehouse": warehouse},
					"actual_qty",
				)
			)
			rate_per_kg = flt(
				frappe.db.get_value(
					"Bin",
					{"item_code": feed_item, "warehouse": warehouse},
					"valuation_rate",
				)
			)

		# Friendly batch name (Batch 1, Batch 2...) instead of ID
		batch_name = f"Batch {idx + 1}"

		# Calculate opening bird count and opening egg stock from previous register (or 1st time defaults)
		opening_birds, opening_eggs = get_batch_opening_figures(b.name, log_dt, b.current_bird_count)

		batch_list.append(
			{
				"batch": b.name,
				"batch_name": batch_name,
				"breed": batch_breed,
				"breed_type": b.breed_type,
				"week_day": week_day_str,
				"days_elapsed": days_elapsed,
				"opening_birds": opening_birds,
				"opening_eggs": opening_eggs,
				"feed_item": feed_item,
				"warehouse": warehouse,
				"opening_stock_kg": stock_qty,
				"rate_per_kg": rate_per_kg,
				"benchmark": {
					"standard_body_weight_g": flt(bmk.get("standard_body_weight_g")),
					"standard_hdep_pct": flt(bmk.get("standard_hdep_pct")),
					"standard_mortality_pct": flt(bmk.get("standard_mortality_pct")),
					"standard_feed_per_bird_g": flt(bmk.get("standard_feed_per_bird_g")),
				}
				if bmk
				else {},
			}
		)

	if not shed_benchmark and breed:
		shed_benchmark = get_benchmark_for_age(breed, 0, batches[0].breed_type if batches else None)

	return {
		"shed_name": shed_doc.shed_name or shed,
		"day_of_week": day_of_week,
		"breed": breed,
		"sex": sex,
		"batches": batch_list,
		"benchmark": {
			"standard_body_weight_g": flt(shed_benchmark.get("standard_body_weight_g")),
			"standard_hdep_pct": flt(shed_benchmark.get("standard_hdep_pct")),
			"standard_mortality_pct": flt(shed_benchmark.get("standard_mortality_pct")),
			"standard_feed_per_bird_g": flt(shed_benchmark.get("standard_feed_per_bird_g")),
		}
		if shed_benchmark
		else {},
	}
