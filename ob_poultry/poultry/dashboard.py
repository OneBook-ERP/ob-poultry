import frappe
from frappe.utils import flt, nowdate


@frappe.whitelist()
def eggs_produced_today():
	return _sum_today("total_eggs_produced")


@frappe.whitelist()
def feed_consumed_today():
	return _sum_today("total_feed_consumed_kg", "feed_consumed_kg")


@frappe.whitelist()
def mortality_today():
	return _sum_today("total_mortality", "mortality_count")


@frappe.whitelist()
def culled_today():
	return _sum_today("total_culled", "cull_count")


def _sum_today(*fieldnames):
	today = nowdate()
	for fn in fieldnames:
		res = frappe.db.sql(
			f"""
			select sum(coalesce({fn}, 0)) as total
			from `tabPoultry Daily Log`
			where log_date = %s and docstatus < 2
			""",
			(today,),
			as_dict=True,
		)
		if res and res[0].total is not None and flt(res[0].total) > 0:
			return flt(res[0].total)
	return 0.0
