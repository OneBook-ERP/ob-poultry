import frappe
from frappe import _


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
		{"label": _("Grade"), "fieldname": "grade", "fieldtype": "Data", "width": 110},
		{"label": _("Produced"), "fieldname": "produced", "fieldtype": "Int", "width": 100},
		{"label": _("Sold"), "fieldname": "sold", "fieldtype": "Int", "width": 100},
		{"label": _("Net Stock"), "fieldname": "net_stock", "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	produced_rows = get_produced(filters)
	sold_map = get_sold_map(filters)

	data = []
	for row in produced_rows:
		key = (row.batch, row.grade)
		sold = sold_map.get(key, 0)
		data.append(
			{
				"batch": row.batch,
				"grade": row.grade,
				"produced": row.produced,
				"sold": sold,
				"net_stock": (row.produced or 0) - sold,
			}
		)
	return data


def get_produced(filters):
	conditions = ["d.docstatus = 1", "d.log_date <= %(as_of_date)s"]
	if filters.get("batch"):
		conditions.append("d.batch = %(batch)s")
	if filters.get("grade"):
		conditions.append("e.grade = %(grade)s")

	return frappe.db.sql(
		f"""
		select d.batch, e.grade, sum(e.production_count) as produced
		from `tabPoultry Daily Log` d
		inner join `tabPoultry Daily Log Egg Entry` e on e.parent = d.name
		where {" and ".join(conditions)}
		group by d.batch, e.grade
		order by d.batch, e.grade
		""",
		filters,
		as_dict=True,
	)


def get_sold_map(filters):
	conditions = ["s.docstatus = 1", "s.sale_date <= %(as_of_date)s"]
	if filters.get("batch"):
		conditions.append("s.batch = %(batch)s")
	if filters.get("grade"):
		conditions.append("i.grade = %(grade)s")

	sold_rows = frappe.db.sql(
		f"""
		select s.batch, i.grade, sum(i.quantity) as sold
		from `tabPoultry Egg Sale` s
		inner join `tabPoultry Egg Sale Item` i on i.parent = s.name
		where {" and ".join(conditions)}
		group by s.batch, i.grade
		""",
		filters,
		as_dict=True,
	)
	return {(row.batch, row.grade): row.sold or 0 for row in sold_rows}
