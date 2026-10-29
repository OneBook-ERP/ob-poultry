import frappe
from frappe import _
from frappe.model.document import Document


class PoultryChickTransfer(Document):
	@property
	def hatch_doc(self):
		return frappe.get_doc("Poultry Hatch", self.hatch)

	def validate(self):
		self.validate_against_hatch()

	def validate_against_hatch(self):
		hatch = self.hatch_doc
		if not hatch.actual_chicks:
			return
		already_transferred = (
			frappe.db.sql(
				"""
			select sum(quantity)
			from `tabPoultry Chick Transfer`
			where hatch = %s and docstatus = 1 and name != %s
			""",
				(self.hatch, self.name or ""),
			)[0][0]
			or 0
		)
		total_transferred = already_transferred + (self.quantity or 0)
		if total_transferred > hatch.actual_chicks:
			frappe.throw(
				_("Total chicks transferred ({0}) would exceed the actual chicks ({1}) for hatch {2}").format(
					total_transferred, hatch.actual_chicks, hatch.name
				)
			)
