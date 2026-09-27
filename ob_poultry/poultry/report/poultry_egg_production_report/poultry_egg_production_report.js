frappe.query_reports["Poultry Egg Production Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "batch",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Poultry Batch",
		},
		{
			fieldname: "grade",
			label: __("Grade"),
			fieldtype: "Select",
			options: "\nHatching Egg\nTable Egg\nJumbo Egg\nCracked Egg\nWaste Egg",
		},
	],
};
