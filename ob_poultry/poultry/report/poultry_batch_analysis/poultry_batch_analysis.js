frappe.query_reports["Poultry Batch Analysis"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("Start Date From"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("Start Date To"),
			fieldtype: "Date",
		},
		{
			fieldname: "flock_source",
			label: __("Flock Source"),
			fieldtype: "Select",
			options: "\nOwned\nContract",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nActive\nClosed",
		},
	],
};
