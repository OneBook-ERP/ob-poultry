// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Poultry Hatchery", {
	onload(frm) {
		sync_location_options(frm);
	},
	refresh(frm) {
		sync_location_options(frm);
	},
});

function sync_location_options(frm) {
	frappe.db.get_list("Location", { fields: ["name"], limit: 100 }).then((locations) => {
		let current_options = (frm.fields_dict.location.df.options || "").split("\n");
		let db_locations = (locations || []).map((l) => l.name).filter(Boolean);
		let combined = [...new Set([...current_options, ...db_locations])];
		frm.set_df_property("location", "options", combined.join("\n"));
	});
}
