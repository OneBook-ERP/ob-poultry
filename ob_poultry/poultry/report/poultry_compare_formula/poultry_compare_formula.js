frappe.query_reports["Poultry Compare Formula"] = {
	filters: [
		{
			fieldname: "is_active",
			label: __("Active Formulas Only"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
