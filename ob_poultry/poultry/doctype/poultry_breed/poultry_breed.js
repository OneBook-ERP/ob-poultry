function populate_days_lineup(frm) {
	const breed_type = frm.doc.breed_type || "Broiler";
	frappe.call({
		method: "ob_poultry.poultry.doctype.poultry_breed.poultry_breed.get_default_days_lineup",
		args: { breed_type: breed_type },
		callback(r) {
			if (r.message && Array.isArray(r.message)) {
				frm.clear_table("benchmarks");
				for (let row_data of r.message) {
					let row = frm.add_child("benchmarks");
					row.from_day = row_data.from_day;
					row.to_day = row_data.to_day;
					row.age_in_days = row_data.age_in_days;
					row.day_start = row_data.day_start;
					row.day_end = row_data.day_end;
					row.standard_mortality_pct = null;
					row.standard_feed_per_bird_g = null;
					row.standard_body_weight_g = null;
					row.standard_fcr = null;
				}
				frm.refresh_field("benchmarks");
			}
		},
	});
}

function load_default_values(frm) {
	const breed_type = frm.doc.breed_type || "Broiler";
	frappe.call({
		method: "ob_poultry.poultry.doctype.poultry_breed.poultry_breed.get_default_benchmarks",
		args: { breed_type: breed_type },
		callback(r) {
			if (r.message && Array.isArray(r.message)) {
				// If row count matches current rows, update metric values in place preserving any custom bounds
				if (frm.doc.benchmarks && frm.doc.benchmarks.length === r.message.length) {
					for (let i = 0; i < r.message.length; i++) {
						let row = frm.doc.benchmarks[i];
						let data = r.message[i];
						row.standard_mortality_pct = data.standard_mortality_pct;
						row.standard_feed_per_bird_g = data.standard_feed_per_bird_g;
						row.standard_body_weight_g = data.standard_body_weight_g;
						row.standard_fcr = data.standard_fcr;
					}
				} else {
					frm.clear_table("benchmarks");
					for (let row_data of r.message) {
						let row = frm.add_child("benchmarks");
						row.from_day = row_data.from_day;
						row.to_day = row_data.to_day;
						row.age_in_days = row_data.age_in_days;
						row.day_start = row_data.day_start;
						row.day_end = row_data.day_end;
						row.standard_mortality_pct = row_data.standard_mortality_pct;
						row.standard_feed_per_bird_g = row_data.standard_feed_per_bird_g;
						row.standard_body_weight_g = row_data.standard_body_weight_g;
						row.standard_fcr = row_data.standard_fcr;
					}
				}
				frm.refresh_field("benchmarks");
				frappe.show_alert({
					message: __("Loaded real-world default benchmark values for {0}", [breed_type]),
					indicator: "green",
				});
			}
		},
	});
}

frappe.ui.form.on("Poultry Breed", {
	onload(frm) {
		// When creating a new breed, automatically show the days lineup with metric columns empty
		if (frm.is_new() && (!frm.doc.benchmarks || frm.doc.benchmarks.length === 0)) {
			populate_days_lineup(frm);
		}
	},

	refresh(frm) {
		// Button to load real-world default values on demand (always asks for confirmation)
		frm.add_custom_button(__("Load Default Values"), () => {
			const breed_type = frm.doc.breed_type || "Broiler";
			frappe.confirm(
				__("Are you sure you want to load default benchmark values for {0}?", [breed_type]),
				() => {
					load_default_values(frm);
				}
			);
		});

		// Button to reset/load empty days lineup if table is cleared
		if (!frm.doc.benchmarks || frm.doc.benchmarks.length === 0) {
			frm.add_custom_button(__("Load Days Lineup"), () => {
				populate_days_lineup(frm);
			});
		}
	},

	breed_type(frm) {
		if (frm.doc.breed_type) {
			let has_metrics = (frm.doc.benchmarks || []).some(
				(r) => (r.standard_body_weight_g > 0 || r.standard_feed_per_bird_g > 0 || r.standard_mortality_pct > 0 || r.standard_fcr > 0)
			);
			if (has_metrics) {
				frappe.confirm(
					__("Update days lineup to match {0}? Existing metric values will be replaced.", [frm.doc.breed_type]),
					() => {
						populate_days_lineup(frm);
					}
				);
			} else {
				populate_days_lineup(frm);
			}
		}
	},
});

function sync_day_bounds(cdt, cdn) {
	let row = locals[cdt][cdn];
	let from_day = (row.from_day !== null && row.from_day !== undefined) ? parseInt(row.from_day, 10) : null;
	let to_day = (row.to_day !== null && row.to_day !== undefined) ? parseInt(row.to_day, 10) : null;

	if (!isNaN(from_day) && from_day !== null) {
		frappe.model.set_value(cdt, cdn, "day_start", from_day);
	}
	if (!isNaN(to_day) && to_day !== null) {
		frappe.model.set_value(cdt, cdn, "day_end", to_day);
	}
	if (!isNaN(from_day) && !isNaN(to_day) && from_day !== null && to_day !== null) {
		frappe.model.set_value(cdt, cdn, "age_in_days", `${from_day}-${to_day}`);
	}
}

frappe.ui.form.on("Poultry Breed Benchmark", {
	from_day(frm, cdt, cdn) {
		sync_day_bounds(cdt, cdn);
	},
	to_day(frm, cdt, cdn) {
		sync_day_bounds(cdt, cdn);
	},
});
