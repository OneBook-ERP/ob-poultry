import frappe
from frappe.model.document import Document


class PoultryShed(Document):
	def validate(self):
		if self.capacity and self.capacity < 0:
			frappe.throw("Capacity cannot be negative")
