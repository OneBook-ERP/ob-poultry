import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class PoultryBatch(Document):
	def validate(self):
		self.validate_shed_capacity()
		self.validate_contract_fields()
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

	def validate_contract_fields(self):
		if self.flock_source != "Contract":
			return
		if not self.farmer:
			frappe.throw(_("Set a Farmer for a Contract flock"))
		if not self.growing_charge_scheme:
			frappe.throw(_("Set a Growing Charge Scheme for a Contract flock"))

	def after_insert(self):
		self.create_vaccination_due_rows()

	def create_vaccination_due_rows(self):
		template_name = frappe.db.get_value(
			"Poultry Vaccination Schedule Template", {"breed": self.breed, "is_active": 1}
		)
		if not template_name:
			return
		template = frappe.get_doc("Poultry Vaccination Schedule Template", template_name)
		for row in template.get_due_rows(self.name, self.start_date):
			frappe.get_doc({"doctype": "Poultry Vaccination Due", **row}).insert(ignore_permissions=True)

	@frappe.whitelist()
	def close_batch(self):
		if self.status == "Closed":
			frappe.throw(_("Batch {0} is already closed").format(self.name))
		self.status = "Closed"
		self.end_date = self.end_date or nowdate()
		self.save()

	@frappe.whitelist()
	def calculate_growing_charge(self):
		if self.flock_source != "Contract" or not self.growing_charge_scheme:
			frappe.throw(_("Set Flock Source to Contract and choose a Growing Charge Scheme first"))
		latest_weight_g = frappe.db.get_value(
			"Poultry Daily Log",
			{"batch": self.name, "docstatus": 1, "average_body_weight_g": [">", 0]},
			"average_body_weight_g",
			order_by="log_date desc",
		)
		if not latest_weight_g:
			frappe.throw(_("No body weight has been recorded for batch {0} yet").format(self.name))
		scheme = frappe.get_doc("Poultry Growing Charge Scheme", self.growing_charge_scheme)
		rate_per_kg = scheme.get_rate_for_weight(latest_weight_g)
		total_weight_kg = flt(self.current_bird_count) * flt(latest_weight_g) / 1000
		amount = total_weight_kg * flt(rate_per_kg)
		self.db_set("growing_charge_amount", amount)
		return amount

	def recalculate_performance(self):
		totals = frappe.db.sql(
			"""
			select
				sum(mortality_count) as mortality,
				sum(cull_count) as cull,
				sum(feed_consumed_kg) as feed_kg
			from `tabPoultry Daily Log`
			where batch = %s and docstatus = 1
			""",
			self.name,
			as_dict=True,
		)[0]
		mortality = totals.mortality or 0
		removed = mortality + (totals.cull or 0)
		current_bird_count = self.initial_bird_count - removed
		cumulative_feed_kg = totals.feed_kg or 0

		latest_weight_g = frappe.db.get_value(
			"Poultry Daily Log",
			{"batch": self.name, "docstatus": 1, "average_body_weight_g": [">", 0]},
			"average_body_weight_g",
			order_by="log_date desc",
		)
		fcr = 0
		cfcr = 0
		if latest_weight_g and current_bird_count > 0:
			live_weight_kg = current_bird_count * flt(latest_weight_g) / 1000
			mortality_weight_kg = mortality * flt(latest_weight_g) / 1000
			if live_weight_kg:
				fcr = cumulative_feed_kg / live_weight_kg
			if live_weight_kg + mortality_weight_kg:
				cfcr = cumulative_feed_kg / (live_weight_kg + mortality_weight_kg)

		frappe.db.set_value(
			self.doctype,
			self.name,
			{
				"total_mortality": mortality,
				"current_bird_count": current_bird_count,
				"cumulative_feed_kg": cumulative_feed_kg,
				"fcr": fcr,
				"cfcr": cfcr,
			},
			update_modified=False,
		)
