import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, flt


class PoultryDailyLog(Document):
	@property
	def batch_doc(self):
		return frappe.get_doc("Poultry Batch", self.batch)

	def validate(self):
		self.validate_unique_log()
		self.validate_batch_not_closed()
		self.compute_mortality_rollup()
		self.validate_bird_count()
		self.compute_egg_rollup()
		self.apply_benchmarks()

	def validate_unique_log(self):
		existing = frappe.db.exists(
			"Poultry Daily Log",
			{"batch": self.batch, "log_date": self.log_date, "name": ["!=", self.name or ""]},
		)
		if existing:
			frappe.throw(_("A log for batch {0} on {1} already exists: {2}").format(self.batch, self.log_date, existing))

	def validate_batch_not_closed(self):
		if self.batch_doc.status == "Closed":
			frappe.throw(_("Batch {0} is closed and cannot receive new daily logs").format(self.batch))

	def compute_mortality_rollup(self):
		self.mortality_count = sum(flt(row.count) for row in self.mortality_details) if self.mortality_details else 0

	def validate_bird_count(self):
		batch = self.batch_doc
		removed_elsewhere = frappe.db.sql(
			"""
			select sum(mortality_count) + sum(cull_count) as removed
			from `tabPoultry Daily Log`
			where batch = %s and docstatus = 1 and name != %s
			""",
			(self.batch, self.name or ""),
			as_dict=True,
		)[0].removed or 0
		total_removed = removed_elsewhere + (self.mortality_count or 0) + (self.cull_count or 0)
		if total_removed > batch.initial_bird_count:
			frappe.throw(
				_("Total removed birds ({0}) would exceed the initial bird count ({1}) for batch {2}").format(
					total_removed, batch.initial_bird_count, batch.name
				)
			)

	def compute_egg_rollup(self):
		total = 0
		for row in self.egg_entries:
			row.opening_count = self.get_previous_closing(row.grade)
			row.closing_count = flt(row.opening_count) + flt(row.production_count)
			total += flt(row.production_count)
		self.total_eggs_produced = total
		current_bird_count = self.batch_doc.current_bird_count
		self.hdep_percent = (total / current_bird_count * 100) if current_bird_count else 0

	def get_previous_closing(self, grade):
		result = frappe.db.sql(
			"""
			select e.closing_count
			from `tabPoultry Daily Log Egg Entry` e
			inner join `tabPoultry Daily Log` d on d.name = e.parent
			where d.batch = %s and d.docstatus = 1 and d.log_date < %s and e.grade = %s
			order by d.log_date desc
			limit 1
			""",
			(self.batch, self.log_date, grade),
		)
		return result[0][0] if result else 0

	def apply_benchmarks(self):
		batch = self.batch_doc
		age_in_days = date_diff(self.log_date, batch.start_date)
		benchmark = frappe.db.sql(
			"""
			select standard_mortality_pct, standard_feed_per_bird_g, standard_body_weight_g
			from `tabPoultry Benchmark`
			where breed = %s and age_in_days <= %s
			order by age_in_days desc
			limit 1
			""",
			(batch.breed, age_in_days),
			as_dict=True,
		)
		if not benchmark:
			self.std_mortality_pct = None
			self.std_feed_per_bird_g = None
			self.std_body_weight_g = None
			return
		self.std_mortality_pct = benchmark[0].standard_mortality_pct
		self.std_feed_per_bird_g = benchmark[0].standard_feed_per_bird_g
		self.std_body_weight_g = benchmark[0].standard_body_weight_g

	def on_submit(self):
		self.create_feed_stock_entry()
		self.batch_doc.recalculate_performance()

	def on_cancel(self):
		if self.stock_entry:
			stock_entry = frappe.get_doc("Stock Entry", self.stock_entry)
			if stock_entry.docstatus == 1:
				stock_entry.cancel()
		self.batch_doc.recalculate_performance()

	def create_feed_stock_entry(self):
		if not self.feed_consumed_kg:
			return
		if not self.feed_item:
			frappe.throw(_("Set a Feed Item to log feed consumption"))
		batch = self.batch_doc
		if not batch.feed_warehouse:
			frappe.throw(
				_("Set a Feed Warehouse on Poultry Batch {0} before logging feed consumption").format(batch.name)
			)
		stock_entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Issue",
				"company": frappe.db.get_value("Warehouse", batch.feed_warehouse, "company"),
				"items": [
					{
						"item_code": self.feed_item,
						"qty": self.feed_consumed_kg,
						"s_warehouse": batch.feed_warehouse,
					}
				],
			}
		)
		stock_entry.insert(ignore_permissions=True)
		stock_entry.submit()
		self.db_set("stock_entry", stock_entry.name)
