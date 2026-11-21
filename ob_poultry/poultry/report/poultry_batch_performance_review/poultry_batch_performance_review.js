frappe.query_reports["Poultry Batch Performance Review"] = {
	filters: [
		{
			fieldname: "shed",
			label: __("Shed"),
			fieldtype: "Link",
			options: "Poultry Shed",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nActive\nClosed",
		},
		{
			fieldname: "flock_source",
			label: __("Flock Source"),
			fieldtype: "Select",
			options: "\nOwned\nContract",
		},
	],
};
