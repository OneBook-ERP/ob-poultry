# Copyright (c) 2026, OB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum


class PoultryChickTransfer(Document):
	@property
	def hatch_doc(self):
		return frappe.get_doc("Poultry Hatch", self.hatch)

	def validate(self):
		self.validate_against_hatch()

	def validate_against_hatch(self):
		hatch = self.hatch_doc
		actual = hatch.get("actual_chicks") or hatch.get("initial_bird_count")
		if not actual:
			return

		transfer = frappe.qb.DocType("Poultry Chick Transfer")
		query = (
			frappe.qb.from_(transfer)
			.select(Sum(transfer.quantity))
			.where((transfer.hatch == self.hatch) & (transfer.docstatus == 1))
		)
		if self.name:
			query = query.where(transfer.name != self.name)

		already_transferred = query.run()[0][0] or 0
		total_transferred = already_transferred + (self.quantity or 0)
		if total_transferred > actual:
			frappe.throw(
				_("Total chicks transferred ({0}) would exceed the actual chicks ({1}) for hatch {2}").format(
					total_transferred, actual, hatch.name
				)
			)
