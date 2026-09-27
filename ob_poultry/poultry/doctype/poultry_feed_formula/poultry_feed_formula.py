import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class PoultryFeedFormula(Document):
	def validate(self):
		self.calculate_percentages()

	def calculate_percentages(self):
		for ingredient in self.ingredients:
			ingredient.percentage = (
				flt(ingredient.quantity_kg) / flt(self.batch_size_kg) * 100 if self.batch_size_kg else 0
			)

	@frappe.whitelist()
	def create_or_update_bom(self):
		if not self.ingredients:
			frappe.throw(_("Add ingredients before creating a BOM"))

		if self.bom and frappe.db.exists("BOM", self.bom):
			bom = frappe.get_doc("BOM", self.bom)
			if bom.docstatus == 1:
				bom.cancel()
			bom.items = []
		else:
			bom = frappe.new_doc("BOM")
			bom.item = self.feed_item

		bom.company = bom.company or self.get_default_company()
		bom.quantity = self.batch_size_kg
		for ingredient in self.ingredients:
			bom.append("items", {"item_code": ingredient.raw_material, "qty": ingredient.quantity_kg})

		if bom.is_new():
			bom.insert(ignore_permissions=True)
		else:
			bom.save(ignore_permissions=True)
		bom.submit()

		self.db_set("bom", bom.name)
		return bom.name

	@frappe.whitelist()
	def make_work_order(self, planned_qty):
		if not self.bom:
			frappe.throw(_("Create a BOM for {0} first").format(self.name))

		work_order = frappe.get_doc(
			{
				"doctype": "Work Order",
				"production_item": self.feed_item,
				"bom_no": self.bom,
				"qty": flt(planned_qty),
				"company": self.get_default_company(),
				"planned_start_date": now_datetime(),
			}
		)
		work_order.insert(ignore_permissions=True)
		return work_order.name

	def get_default_company(self):
		company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		if not company:
			companies = frappe.get_all("Company", limit=1, pluck="name")
			company = companies[0] if companies else None
		if not company:
			frappe.throw(_("Set up a Company in ERPNext before creating a BOM or Work Order"))
		return company
