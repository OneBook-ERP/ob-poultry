import frappe
from frappe import _
from frappe.model.document import Document


class PoultryVaccinationRecord(Document):
	def validate(self):
		if self.next_due_date and self.next_due_date <= self.date_given:
			frappe.throw(_("Next Due Date must be after Date Given"))

	def on_update(self):
		if self.due:
			frappe.db.set_value(
				"Poultry Vaccination Due", self.due, {"status": "Done", "vaccination_record": self.name}
			)
