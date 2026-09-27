frappe.query_reports["Poultry Feed Production Summary"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			description: __("Poultry Feed Production has no date field of its own; this filters on its creation timestamp."),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			description: __("Poultry Feed Production has no date field of its own; this filters on its creation timestamp."),
		},
		{
			fieldname: "formula",
			label: __("Formula"),
			fieldtype: "Link",
			options: "Poultry Feed Formula",
		},
	],
};
