import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class PoultryBatch(Document):
	def validate(self):
		self.validate_shed_capacity()
		if self.is_new():
			self.current_bird_count = self.initial_bird_count

	def validate_shed_capacity(self):
		capacity = frappe.db.get_value("Poultry Shed", self.shed, "capacity")
		if capacity and self.initial_bird_count > capacity:
			frappe.throw(
				_("Initial Bird Count ({0}) exceeds the capacity ({1}) of Shed {2}").format(
					self.initial_bird_count, capacity, self.shed
				)
			)

	@frappe.whitelist()
	def close_batch(self):
		if self.status == "Closed":
			frappe.throw(_("Batch {0} is already closed").format(self.name))
		self.status = "Closed"
		self.end_date = self.end_date or nowdate()
		self.save()

	def recalculate_bird_count(self):
		totals = frappe.db.sql(
			"""
			select sum(mortality_count) as mortality, sum(cull_count) as cull
			from `tabPoultry Daily Log`
			where batch = %s and docstatus = 1
			""",
			self.name,
			as_dict=True,
		)[0]
		mortality = totals.mortality or 0
		removed = mortality + (totals.cull or 0)
		frappe.db.set_value(
			self.doctype,
			self.name,
			{
				"total_mortality": mortality,
				"current_bird_count": self.initial_bird_count - removed,
			},
			update_modified=False,
		)
