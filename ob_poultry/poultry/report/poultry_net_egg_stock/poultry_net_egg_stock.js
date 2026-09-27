frappe.query_reports["Poultry Net Egg Stock"] = {
	filters: [
		{
			fieldname: "as_of_date",
			label: __("As Of Date"),
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
			options: "\nHatching Egg\nTable Egg\nJumbo Egg\nCracked Egg\nWaste Egg\nDouble Yolk\nDirty Egg",
		},
	],
};
