import frappe
from frappe import _
from frappe.model.document import Document


class PoultryDailyLog(Document):
	@property
	def batch_doc(self):
		return frappe.get_doc("Poultry Batch", self.batch)

	def validate(self):
		self.validate_unique_log()
		self.validate_bird_count()

	def validate_unique_log(self):
		existing = frappe.db.exists(
			"Poultry Daily Log",
			{"batch": self.batch, "log_date": self.log_date, "name": ["!=", self.name or ""]},
		)
		if existing:
			frappe.throw(_("A log for batch {0} on {1} already exists: {2}").format(self.batch, self.log_date, existing))

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

	def on_submit(self):
		self.create_feed_stock_entry()
		self.batch_doc.recalculate_bird_count()

	def on_cancel(self):
		if self.stock_entry:
			stock_entry = frappe.get_doc("Stock Entry", self.stock_entry)
			if stock_entry.docstatus == 1:
				stock_entry.cancel()
		self.batch_doc.recalculate_bird_count()

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
