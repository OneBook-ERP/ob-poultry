// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Poultry Egg Sale", {
	setup(frm) {
		frm.egg_rate_info = null;
	},
	refresh(frm) {
		fetch_market_egg_rate(frm);
		calculate_total(frm);
	},
	sale_date(frm) {
		fetch_market_egg_rate(frm);
	},
	items_remove(frm) {
		calculate_total(frm);
	}
});

frappe.ui.form.on("Poultry Egg Sale Item", {
	items_add(frm, cdt, cdn) {
		apply_market_rate_to_row(frm, cdt, cdn);
	},
	grade(frm, cdt, cdn) {
		apply_market_rate_to_row(frm, cdt, cdn);
	},
	quantity(frm, cdt, cdn) {
		calculate_row_amount(frm, cdt, cdn);
	},
	rate(frm, cdt, cdn) {
		calculate_row_amount(frm, cdt, cdn);
	}
});

function fetch_market_egg_rate(frm) {
	frappe.call({
		method: "ob_poultry.poultry.utils.mkisan_api.get_today_egg_rate",
		args: {
			date: frm.doc.sale_date
		},
		callback(r) {
			if (r.message && r.message.success) {
				frm.egg_rate_info = r.message;
				let info = r.message;
				
				let fetched_time = "";
				if (info.synced_at && window.moment) {
					fetched_time = moment(info.synced_at).format("DD MMM, hh:mm A");
				} else {
					fetched_time = (info.synced_at || "").split(".")[0];
				}

				let rate_date_str = "";
				if (info.rate_date && window.moment) {
					rate_date_str = moment(info.rate_date).format("DD MMM YYYY");
				} else {
					rate_date_str = info.rate_date || "";
				}

				let piece_str = flt(info.rate_per_piece).toFixed(2);
				let tray_str = flt(info.rate_per_tray).toFixed(2);
				let badge_text = `NECC Rate (${info.market}): ₹${piece_str} / egg (₹${tray_str} / tray) • Rate Date: ${rate_date_str} • Fetched: ${fetched_time}`;
				
				let badge_html = `<div style="margin-top: 5px; font-size: 11px; color: var(--text-muted); font-weight: 500;">
					${badge_text}
				</div>`;

				// Small badge text right above/below the items table
				frm.set_df_property("items", "description", badge_html);

				// Also display as helper description under the Rate field in the row edit modal
				if (frm.fields_dict && frm.fields_dict["items"] && frm.fields_dict["items"].grid) {
					frm.fields_dict["items"].grid.update_docfield_property("rate", "description", badge_text);
				}

				// Auto-fill existing rows if market_rate is missing
				(frm.doc.items || []).forEach(row => {
					if (!row.market_rate) {
						frappe.model.set_value(row.doctype, row.name, "market_rate", flt(info.rate_per_piece));
						if (!row.rate || flt(row.rate) === 0) {
							frappe.model.set_value(row.doctype, row.name, "rate", flt(info.rate_per_piece));
						}
					}
				});
				frm.refresh_field("items");
			}
		}
	});
}

function apply_market_rate_to_row(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (frm.egg_rate_info && frm.egg_rate_info.rate_per_piece) {
		let piece_rate = flt(frm.egg_rate_info.rate_per_piece);
		frappe.model.set_value(cdt, cdn, "market_rate", piece_rate);
		if (!row.rate || flt(row.rate) === 0) {
			frappe.model.set_value(cdt, cdn, "rate", piece_rate);
		}
	}
	calculate_row_amount(frm, cdt, cdn);
}

function calculate_row_amount(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let qty = flt(row.quantity) || 0;
	let rate = flt(row.rate) || 0;
	frappe.model.set_value(cdt, cdn, "amount", qty * rate);
	calculate_total(frm);
}

function calculate_total(frm) {
	let total = 0;
	(frm.doc.items || []).forEach(row => {
		total += flt(row.amount) || 0;
	});
	frm.set_value("total_amount", total);
}
