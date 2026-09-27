from frappe.model.document import Document
from frappe.utils import flt


class PoultryHatch(Document):
	def validate(self):
		if self.standard_hatchability_pct:
			self.estimated_chicks = round(flt(self.eggs_set) * flt(self.standard_hatchability_pct) / 100)
		else:
			self.estimated_chicks = None
