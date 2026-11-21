import frappe
from frappe.model.document import Document


class PoultryShed(Document):
	def validate(self):
		if self.capacity and self.capacity < 0:
			frappe.throw("Capacity cannot be negative")
		if not self.default_egg_warehouse:
			self.default_egg_warehouse = frappe.db.get_single_value(
				"Poultry Settings", "default_egg_warehouse"
			)
