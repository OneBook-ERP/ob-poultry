// Copyright (c) 2026
// For license information, please see license.txt

frappe.query_reports["Poultry Chick Stock"] = {
	filters: [
		{
			fieldname: "hatchery",
			label: __("Hatchery"),
			fieldtype: "Link",
			options: "Poultry Hatchery",
		},
	],
};
