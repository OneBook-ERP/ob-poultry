from frappe.model.document import Document
from frappe.utils import flt


class PoultryHatch(Document):
	def validate(self):
		if self.get("standard_hatchability_pct"):
			self.estimated_chicks = round(flt(self.eggs_set) * flt(self.standard_hatchability_pct) / 100)
		elif self.get("estimated_chicks") is not None and not self.get("standard_hatchability_pct"):
			self.estimated_chicks = None
