# Copyright (c) 2026, OB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class PoultryDailyEggRate(Document):
	def validate(self):
		eggs_per_tray = frappe.db.get_single_value("Poultry Settings", "eggs_per_tray") or 30
		if not self.rate_per_tray and self.rate_per_piece:
			self.rate_per_tray = flt(self.rate_per_piece) * eggs_per_tray
		if not self.rate_per_100 and self.rate_per_piece:
			self.rate_per_100 = flt(self.rate_per_piece) * 100
		if not self.rate_per_peti and self.rate_per_piece:
			self.rate_per_peti = flt(self.rate_per_piece) * 210
