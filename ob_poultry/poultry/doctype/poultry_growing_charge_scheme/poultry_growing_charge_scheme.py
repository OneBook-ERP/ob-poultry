import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PoultryGrowingChargeScheme(Document):
	def validate(self):
		for i, row in enumerate(self.rates, start=1):
			if row.max_weight_g and row.max_weight_g <= row.min_weight_g:
				frappe.throw(
					_("Row #{0}: Max Weight ({1}) must be greater than Min Weight ({2})").format(
						i, row.max_weight_g, row.min_weight_g
					)
				)

	def get_rate_for_weight(self, weight_g):
		weight_g = flt(weight_g)
		for row in self.rates:
			if weight_g >= row.min_weight_g and (not row.max_weight_g or weight_g <= row.max_weight_g):
				return row.rate_per_kg
		frappe.throw(_("No rate bracket in scheme {0} covers a weight of {1}g").format(self.name, weight_g))
