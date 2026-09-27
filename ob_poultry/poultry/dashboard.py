import frappe
from frappe.utils import nowdate


@frappe.whitelist()
def eggs_produced_today():
	return _sum_today("total_eggs_produced")


@frappe.whitelist()
def feed_consumed_today():
	return _sum_today("feed_consumed_kg")


@frappe.whitelist()
def mortality_today():
	return _sum_today("mortality_count")


@frappe.whitelist()
def culled_today():
	return _sum_today("cull_count")


def _sum_today(fieldname):
	result = frappe.db.sql(
		f"""
		select sum({fieldname}) as total
		from `tabPoultry Daily Log`
		where log_date = %s and docstatus = 1
		""",
		(nowdate(),),
		as_dict=True,
	)
	return result[0].total or 0
