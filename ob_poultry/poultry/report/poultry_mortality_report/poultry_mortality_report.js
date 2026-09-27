frappe.query_reports["Poultry Mortality Report"] = {
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
			fieldname: "shed",
			label: __("Shed"),
			fieldtype: "Link",
			options: "Poultry Shed",
		},
		{
			fieldname: "breed",
			label: __("Breed"),
			fieldtype: "Link",
			options: "Poultry Breed",
		},
		{
			fieldname: "cause",
			label: __("Cause"),
			fieldtype: "Select",
			options: "\nDisease\nInjury\nHeat Stress\nCulled (Runt or Weak)\nPredator\nUnknown\nOther",
		},
	],
};
