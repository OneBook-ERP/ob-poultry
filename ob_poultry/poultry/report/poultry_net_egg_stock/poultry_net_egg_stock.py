import frappe
from frappe import _
from frappe.utils import cint


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
		{"label": _("Batch Name"), "fieldname": "batch_name", "fieldtype": "Data", "width": 140},
		{
			"label": _("Shed"),
			"fieldname": "shed",
			"fieldtype": "Link",
			"options": "Poultry Shed",
			"width": 120,
		},
		{"label": _("Good Eggs"), "fieldname": "good_eggs", "fieldtype": "Int", "width": 100},
		{"label": _("Double Yolk"), "fieldname": "double_yolk_eggs", "fieldtype": "Int", "width": 100},
		{"label": _("Total Produced"), "fieldname": "total_produced", "fieldtype": "Int", "width": 110},
		{"label": _("Total Sold"), "fieldname": "total_sold", "fieldtype": "Int", "width": 100},
		{"label": _("SO Reserved"), "fieldname": "so_reserved", "fieldtype": "Int", "width": 100},
		{"label": _("Net Available"), "fieldname": "net_stock", "fieldtype": "Int", "width": 110},
		{"label": _("Trays & Left"), "fieldname": "tray_summary", "fieldtype": "Data", "width": 150},
		{
			"label": _("Cold Room Stock"),
			"fieldname": "cold_room_balance",
			"fieldtype": "Int",
			"width": 130,
		},
	]


def get_data(filters):
	as_of_date = filters.get("as_of_date") or frappe.utils.nowdate()
	values = {"as_of_date": as_of_date}

	batch_cond = ""
	if filters.get("batch"):
		batch_cond = " and e.batch = %(batch)s"
		values["batch"] = filters.get("batch")

	shed_cond = ""
	if filters.get("shed"):
		shed_cond = " and e.shed = %(shed)s"
		values["shed"] = filters.get("shed")

	# 1. Total produced up to as_of_date
	produced_rows = frappe.db.sql(
		f"""
		select
			e.batch,
			b.batch_name,
			e.shed,
			sum(e.good_eggs) as good_eggs,
			sum(e.double_yolk_eggs) as double_yolk_eggs,
			sum(e.total_eggs) as total_eggs
		from `tabPoultry Daily Log Egg Entry` e
		inner join `tabPoultry Daily Log` d on d.name = e.parent
		left join `tabPoultry Batch` b on b.name = e.batch
		where d.docstatus = 1 and d.log_date <= %(as_of_date)s {batch_cond} {shed_cond}
		group by e.batch, e.shed
		order by e.batch, e.shed
		""",
		values,
		as_dict=True,
	)

	if not produced_rows:
		return []

	batches = list({r.batch for r in produced_rows if r.batch})

	# 2. Daily Log Sales per batch
	dl_sales = frappe.db.sql(
		"""
		select
			s.batch,
			sum(s.good_eggs + s.double_yolk_eggs + s.broken_eggs) as sold
		from `tabPoultry Daily Log Sales Entry` s
		inner join `tabPoultry Daily Log` d on d.name = s.parent
		where d.docstatus = 1 and d.log_date <= %(as_of_date)s and s.batch in %(batches)s
		group by s.batch
		""",
		{"as_of_date": as_of_date, "batches": batches},
		as_dict=True,
	)
	dl_sales_map = {r.batch: cint(r.sold) for r in dl_sales}

	# 3. ERPNext Sales Invoices / Delivery Notes
	erp_sales_map = {}
	if frappe.db.table_exists("Sales Invoice Item"):
		si_rows = frappe.db.sql(
			"""
			select
				sii.poultry_batch as batch,
				sum(sii.qty) as sold
			from `tabSales Invoice Item` sii
			inner join `tabSales Invoice` si on si.name = sii.parent
			where si.docstatus = 1 and si.posting_date <= %(as_of_date)s and sii.poultry_batch in %(batches)s
			group by sii.poultry_batch
			""",
			{"as_of_date": as_of_date, "batches": batches},
			as_dict=True,
		)
		for r in si_rows:
			erp_sales_map[r.batch] = erp_sales_map.get(r.batch, 0) + cint(r.sold)

	# 4. Open Sales Orders (reserved)
	so_reserved_map = {}
	if frappe.db.table_exists("Sales Order Item"):
		so_rows = frappe.db.sql(
			"""
			select
				soi.poultry_batch as batch,
				sum(soi.qty) as qty
			from `tabSales Order Item` soi
			inner join `tabSales Order` so on so.name = soi.parent
			where so.docstatus = 1
			  and so.status not in ('Completed', 'Cancelled', 'Closed')
			  and soi.poultry_batch in %(batches)s
			group by soi.poultry_batch
			""",
			{"batches": batches},
			as_dict=True,
		)
		so_reserved_map = {r.batch: cint(r.qty) for r in so_rows}

	# 5. Cold room warehouse balance
	default_wh = frappe.db.get_single_value("Poultry Settings", "default_egg_warehouse")
	default_item = frappe.db.get_single_value("Poultry Settings", "default_egg_item")
	if not default_item:
		default_item = frappe.db.get_value(
			"Item", {"item_group": ("in", ["Eggs", "Egg"]), "is_stock_item": 1}, "name"
		)

	wh_cache = {}

	data = []
	for row in produced_rows:
		batch = row.batch
		good_eggs = cint(row.good_eggs)
		dy_eggs = cint(row.double_yolk_eggs)
		sellable = good_eggs + dy_eggs

		# Total sold is combined desk sales + ERPNext sales
		total_sold = dl_sales_map.get(batch, 0) + erp_sales_map.get(batch, 0)
		so_reserved = so_reserved_map.get(batch, 0)

		net_stock = max(0, sellable - total_sold - so_reserved)
		trays = net_stock // 30
		rem_eggs = net_stock % 30
		summary = f"{trays} Trays, {rem_eggs} Eggs" if net_stock > 0 else "0 Eggs"

		# Cold room warehouse balance for this shed
		shed_wh = frappe.db.get_value("Poultry Shed", row.shed, "default_egg_warehouse") if row.shed else None
		wh = shed_wh or default_wh
		cr_balance = 0
		if wh and default_item:
			if wh not in wh_cache:
				wh_cache[wh] = cint(
					frappe.db.get_value("Bin", {"item_code": default_item, "warehouse": wh}, "actual_qty")
					or 0
				)
			cr_balance = wh_cache[wh]

		data.append(
			{
				"batch": batch,
				"batch_name": row.batch_name or batch,
				"shed": row.shed,
				"good_eggs": good_eggs,
				"double_yolk_eggs": dy_eggs,
				"total_produced": cint(row.total_eggs),
				"total_sold": total_sold,
				"so_reserved": so_reserved,
				"net_stock": net_stock,
				"tray_summary": summary,
				"cold_room_balance": cr_balance,
			}
		)

	return data
