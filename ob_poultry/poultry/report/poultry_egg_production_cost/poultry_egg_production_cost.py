import frappe
from frappe import _
from frappe.utils import cint, flt


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Batch"),
			"fieldname": "batch",
			"fieldtype": "Link",
			"options": "Poultry Batch",
			"width": 140,
		},
		{
			"label": _("Shed"),
			"fieldname": "shed",
			"fieldtype": "Link",
			"options": "Poultry Shed",
			"width": 120,
		},
		{"label": _("Good Eggs"), "fieldname": "good_eggs", "fieldtype": "Int", "width": 110},
		{"label": _("Double Yolk"), "fieldname": "double_yolk_eggs", "fieldtype": "Int", "width": 100},
		{"label": _("Broken/Waste"), "fieldname": "broken_waste_eggs", "fieldtype": "Int", "width": 110},
		{"label": _("Total Eggs"), "fieldname": "total_eggs", "fieldtype": "Int", "width": 110},
		{
			"label": _("Feed Consumed (kg)"),
			"fieldname": "feed_spent_kg",
			"fieldtype": "Float",
			"precision": 2,
			"width": 140,
		},
		{"label": _("Feed Cost"), "fieldname": "feed_cost", "fieldtype": "Currency", "width": 120},
		{
			"label": _("Feed Cost/Egg"),
			"fieldname": "cost_per_egg",
			"fieldtype": "Currency",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("HHEP %"),
			"fieldname": "hhep_pct",
			"fieldtype": "Percent",
			"precision": 2,
			"width": 90,
		},
	]


def get_data(filters):
	values = {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
	}

	batch_filter = ""
	if filters.get("batch"):
		batch_filter = " and batch = %(batch)s"
		values["batch"] = filters.get("batch")

	shed_filter = ""
	if filters.get("shed"):
		shed_filter = " and shed = %(shed)s"
		values["shed"] = filters.get("shed")

	date_filter = " and d.log_date between %(from_date)s and %(to_date)s"

	# Aggregate egg production by batch and shed
	egg_rows = frappe.db.sql(
		f"""
		select
			e.batch,
			e.shed,
			sum(e.good_eggs) as good_eggs,
			sum(e.double_yolk_eggs) as double_yolk_eggs,
			sum(e.broken_eggs + e.waste_eggs) as broken_waste_eggs,
			sum(e.total_eggs) as total_eggs,
			count(distinct d.name) as log_days
		from `tabPoultry Daily Log Egg Entry` e
		inner join `tabPoultry Daily Log` d on d.name = e.parent
		where d.docstatus = 1 {date_filter} {batch_filter.replace("batch", "e.batch")} {shed_filter.replace("shed", "e.shed")}
		group by e.batch, e.shed
		""",
		values,
		as_dict=True,
	)

	# Aggregate feed consumption by batch and shed
	feed_rows = frappe.db.sql(
		f"""
		select
			fe.batch,
			fe.shed,
			sum(fe.feed_spent_kg) as feed_spent_kg,
			sum(fe.total_feed_cost) as feed_cost
		from `tabPoultry Daily Log Feed Entry` fe
		inner join `tabPoultry Daily Log` d on d.name = fe.parent
		where d.docstatus = 1 {date_filter} {batch_filter.replace("batch", "fe.batch")} {shed_filter.replace("shed", "fe.shed")}
		group by fe.batch, fe.shed
		""",
		values,
		as_dict=True,
	)
	feed_map = {(r.batch, r.shed): r for r in feed_rows}

	# Combine batches
	all_keys = set((r.batch, r.shed) for r in egg_rows) | set(feed_map.keys())
	data = []

	egg_map = {(r.batch, r.shed): r for r in egg_rows}
	for b, s in sorted(all_keys, key=lambda x: (x[0] or "", x[1] or "")):
		if not b:
			continue
		er = egg_map.get((b, s))
		fr = feed_map.get((b, s))

		good_eggs = cint(er.good_eggs if er else 0)
		dy_eggs = cint(er.double_yolk_eggs if er else 0)
		bw_eggs = cint(er.broken_waste_eggs if er else 0)
		tot_eggs = cint(er.total_eggs if er else 0)
		sellable_eggs = good_eggs + dy_eggs

		feed_spent = flt(fr.feed_spent_kg if fr else 0)
		feed_cost = flt(fr.feed_cost if fr else 0)

		cost_per_egg = round(feed_cost / sellable_eggs, 2) if sellable_eggs > 0 else 0.0

		# Calculate average HHEP % over the period
		initial_birds = cint(frappe.db.get_value("Poultry Batch", b, "initial_bird_count"))
		log_days = er.log_days if er else 1
		hhep = (
			round((tot_eggs / (initial_birds * log_days)) * 100, 2)
			if (initial_birds > 0 and log_days > 0)
			else 0.0
		)

		data.append(
			{
				"batch": b,
				"shed": s or frappe.db.get_value("Poultry Batch", b, "shed"),
				"good_eggs": good_eggs,
				"double_yolk_eggs": dy_eggs,
				"broken_waste_eggs": bw_eggs,
				"total_eggs": tot_eggs,
				"feed_spent_kg": feed_spent,
				"feed_cost": feed_cost,
				"cost_per_egg": cost_per_egg,
				"hhep_pct": hhep,
			}
		)

	return data
