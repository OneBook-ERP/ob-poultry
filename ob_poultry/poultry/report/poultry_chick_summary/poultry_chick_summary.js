// Copyright (c) 2026
// For license information, please see license.txt

frappe.query_reports["Poultry Chick Summary"] = {
	filters: [
		{
			fieldname: "hatchery",
			label: __("Hatchery"),
			fieldtype: "Link",
			options: "Poultry Hatchery",
		},
		{
			fieldname: "from_date",
			label: __("Schedule Date From"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("Schedule Date To"),
			fieldtype: "Date",
		},
	],
};
