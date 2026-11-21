import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}

	formulas = get_formulas(filters)
	if not formulas:
		return get_base_columns(), []

	formula_names = [f.name for f in formulas]
	ingredient_rows = frappe.db.sql(
		"""
		select parent as formula, raw_material, quantity_kg, category
		from `tabPoultry Feed Formula Ingredient`
		where parent in %(formulas)s
		""",
		{"formulas": formula_names},
		as_dict=True,
	)

	columns, formula_fieldnames = get_columns(formulas)
	data = get_data(formulas, formula_fieldnames, ingredient_rows)

	return columns, data


def get_formulas(filters):
	conditions = {}
	if filters.get("is_active") is not None:
		conditions["is_active"] = filters.get("is_active")
	return frappe.get_all(
		"Poultry Feed Formula",
		filters=conditions,
		fields=["name", "batch_size_kg"],
		order_by="feed_name",
	)


def get_base_columns():
	return [
		{
			"label": _("Raw Material"),
			"fieldname": "raw_material",
			"fieldtype": "Link",
			"options": "Item",
			"width": 200,
		}
	]


def get_columns(formulas):
	columns = get_base_columns()
	formula_fieldnames = {}
	for idx, formula in enumerate(formulas):
		fieldname = f"formula_{idx}"
		formula_fieldnames[formula.name] = fieldname
		columns.append(
			{
				"label": formula.name,
				"fieldname": fieldname,
				"fieldtype": "Float",
				"width": 110,
			}
		)
	return columns, formula_fieldnames


def get_data(formulas, formula_fieldnames, ingredient_rows):
	# ingredient -> {formula_name: qty}, and ingredient -> category, in first-seen order
	quantities_by_ingredient = {}
	category_by_ingredient = {}
	for row in ingredient_rows:
		quantities_by_ingredient.setdefault(row.raw_material, {})[row.formula] = row.quantity_kg
		category_by_ingredient.setdefault(row.raw_material, row.category or "Raw Material")

	raw_material_ingredients = sorted([i for i, cat in category_by_ingredient.items() if cat != "Medicine"])
	medicine_ingredients = sorted([i for i, cat in category_by_ingredient.items() if cat == "Medicine"])

	data = []
	for ingredient in raw_material_ingredients:
		data.append(build_row(ingredient, formulas, formula_fieldnames, quantities_by_ingredient))

	if medicine_ingredients:
		data.append(build_divider_row(_("— Medicine —"), formula_fieldnames))
		for ingredient in medicine_ingredients:
			data.append(build_row(ingredient, formulas, formula_fieldnames, quantities_by_ingredient))

	data.append(build_totals_row(formulas, formula_fieldnames))
	return data


def build_row(ingredient, formulas, formula_fieldnames, quantities_by_ingredient):
	row = {"raw_material": ingredient}
	qty_map = quantities_by_ingredient.get(ingredient, {})
	for formula in formulas:
		row[formula_fieldnames[formula.name]] = qty_map.get(formula.name)
	return row


def build_divider_row(label, formula_fieldnames):
	row = {"raw_material": label}
	for fieldname in formula_fieldnames.values():
		row[fieldname] = None
	return row


def build_totals_row(formulas, formula_fieldnames):
	row = {"raw_material": _("Total (kg)")}
	for formula in formulas:
		row[formula_fieldnames[formula.name]] = formula.batch_size_kg
	return row
