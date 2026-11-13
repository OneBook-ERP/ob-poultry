import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PoultryEggSale(Document):
	def validate(self):
		self.compute_item_amounts()
		self.validate_against_stock()

	def compute_item_amounts(self):
		total = 0
		for row in self.items:
			row.amount = flt(row.quantity) * flt(row.rate)
			total += row.amount
		self.total_amount = total

	def validate_against_stock(self):
		grade_totals = {}
		for row in self.items:
			grade_totals[row.grade] = grade_totals.get(row.grade, 0) + flt(row.quantity)
		for grade, quantity in grade_totals.items():
			available = self.get_available_stock(grade)
			if quantity > available:
				frappe.throw(
					_("Cannot sell {0} {1} eggs for batch {2}: only {3} available in stock as of {4}").format(
						quantity, grade, self.batch, available, self.sale_date
					)
				)

	def get_available_stock(self, grade):
		produced = (
			frappe.db.sql(
				"""
			select sum(e.production_count)
			from `tabPoultry Daily Log Egg Entry` e
			inner join `tabPoultry Daily Log` d on d.name = e.parent
			where d.batch = %s and d.docstatus = 1 and d.log_date <= %s and e.grade = %s
			""",
				(self.batch, self.sale_date, grade),
			)[0][0]
			or 0
		)
		sold_elsewhere = (
			frappe.db.sql(
				"""
			select sum(i.quantity)
			from `tabPoultry Egg Sale Item` i
			inner join `tabPoultry Egg Sale` s on s.name = i.parent
			where s.batch = %s and s.docstatus = 1 and s.name != %s and s.sale_date <= %s and i.grade = %s
			""",
				(self.batch, self.name or "", self.sale_date, grade),
			)[0][0]
			or 0
		)
		return produced - sold_elsewhere
