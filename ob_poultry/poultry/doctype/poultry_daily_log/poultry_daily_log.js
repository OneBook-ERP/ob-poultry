frappe.ui.form.on("Poultry Daily Log", {
	refresh(frm) {
		calculate_mortality(frm);
		calculate_eggs(frm);
	},
	mortality_details_remove(frm) {
		calculate_mortality(frm);
	},
	egg_entries_remove(frm) {
		calculate_eggs(frm);
	}
});

frappe.ui.form.on("Poultry Daily Log Mortality Entry", {
	count(frm, cdt, cdn) {
		calculate_mortality(frm);
	}
});

frappe.ui.form.on("Poultry Daily Log Egg Entry", {
	production_count(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		let eggs_per_tray = 30;
		frappe.model.set_value(cdt, cdn, "trays", (flt(row.production_count) || 0) / eggs_per_tray);
		calculate_eggs(frm);
	}
});

function calculate_mortality(frm) {
	let total = 0;
	(frm.doc.mortality_details || []).forEach(row => {
		total += flt(row.count) || 0;
	});
	frm.set_value("mortality_count", total);
}

function calculate_eggs(frm) {
	let total = 0;
	(frm.doc.egg_entries || []).forEach(row => {
		total += flt(row.production_count) || 0;
	});
	frm.set_value("total_eggs_produced", total);
}
