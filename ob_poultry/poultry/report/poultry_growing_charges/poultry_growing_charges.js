// Copyright (c) 2026
// For license information, please see license.txt

frappe.query_reports["Poultry Growing Charges"] = {
	filters: [
		{
			fieldname: "farmer",
			label: __("Farmer"),
			fieldtype: "Link",
			options: "Poultry Farmer",
		},
		{
			fieldname: "growing_charge_scheme",
			label: __("Scheme"),
			fieldtype: "Link",
			options: "Poultry Growing Charge Scheme",
		},
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
	],
};
