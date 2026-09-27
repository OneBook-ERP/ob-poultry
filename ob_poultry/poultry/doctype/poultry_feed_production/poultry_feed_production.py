import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class PoultryFeedProduction(Document):
	def validate(self):
		self.set_planned_qty()
		self.calculate_yield()

	def set_planned_qty(self):
		batch_size_kg = frappe.db.get_value("Poultry Feed Formula", self.formula, "batch_size_kg")
		self.planned_qty_kg = flt(batch_size_kg) * flt(self.planned_batches)

	def calculate_yield(self):
		if self.actual_output_kg and self.planned_qty_kg:
			self.yield_percent = flt(self.actual_output_kg) / flt(self.planned_qty_kg) * 100
		else:
			self.yield_percent = None

	@frappe.whitelist()
	def create_work_order(self):
		if not self.formula:
			frappe.throw(_("Set a Formula before creating a Work Order"))

		formula_doc = frappe.get_doc("Poultry Feed Formula", self.formula)
		if not formula_doc.bom:
			formula_doc.create_or_update_bom()

		work_order = frappe.get_doc(
			{
				"doctype": "Work Order",
				"production_item": formula_doc.feed_item,
				"bom_no": formula_doc.bom,
				"qty": flt(self.planned_qty_kg),
				"company": self.get_default_company(),
				"planned_start_date": now_datetime(),
			}
		)
		work_order.insert(ignore_permissions=True)

		self.db_set("work_order", work_order.name)
		return work_order.name

	def get_default_company(self):
		company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		if not company:
			companies = frappe.get_all("Company", limit=1, pluck="name")
			company = companies[0] if companies else None
		if not company:
			frappe.throw(_("Set up a Company in ERPNext before creating a Work Order"))
		return company

	# cost_per_kg is left unset here by design: it depends on the linked Work Order's
	# actual completed costing, which isn't wired up yet (FRD.md SS2.7). Fill it once
	# that flow exists rather than approximating it now.
