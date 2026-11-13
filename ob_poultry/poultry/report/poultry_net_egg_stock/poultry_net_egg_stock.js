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
			fieldname: "shed",
			label: __("Shed"),
			fieldtype: "Link",
			options: "Poultry Shed",
		},
		{
			fieldname: "batch",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Poultry Batch",
		},
	],
};
