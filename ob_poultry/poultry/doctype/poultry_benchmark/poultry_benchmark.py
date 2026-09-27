import frappe
from frappe import _
from frappe.model.document import Document


class PoultryBenchmark(Document):
	def validate(self):
		existing = frappe.db.exists(
			"Poultry Benchmark",
			{"breed": self.breed, "age_in_days": self.age_in_days, "name": ["!=", self.name or ""]},
		)
		if existing:
			frappe.throw(
				_("A benchmark for breed {0} at age {1} already exists: {2}").format(
					self.breed, self.age_in_days, existing
				)
			)
