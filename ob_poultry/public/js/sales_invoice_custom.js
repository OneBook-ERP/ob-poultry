// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Invoice", {
	setup(frm) {
		setup_customer_query(frm);
		setup_item_query(frm);
		hide_unwanted_fields(frm);
	},

	onload(frm) {
		setup_customer_query(frm);
		hide_unwanted_fields(frm);
	},

	refresh(frm) {
		setup_customer_query(frm);
		hide_unwanted_fields(frm);
		setup_egg_rate_actions(frm);
		fetch_and_display_egg_rates(frm);
	},
});

frappe.ui.form.on("Sales Invoice Item", {
	item_code(frm, cdt, cdn) {
		auto_apply_egg_rate_to_row(frm, cdt, cdn);
	},

	uom(frm, cdt, cdn) {
		auto_apply_egg_rate_to_row(frm, cdt, cdn);
	},

	is_weight_based_live_bird_sale(frm, cdt, cdn) {
		calculate_weight_based_live_bird(frm, cdt, cdn);
	},
	gross_weight_kg(frm, cdt, cdn) {
		calculate_weight_based_live_bird(frm, cdt, cdn);
	},
	tare_weight_kg(frm, cdt, cdn) {
		calculate_weight_based_live_bird(frm, cdt, cdn);
	},
	birds_count(frm, cdt, cdn) {
		calculate_weight_based_live_bird(frm, cdt, cdn);
	},
});

function calculate_weight_based_live_bird(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (!row) return;

	let gross = flt(row.gross_weight_kg) || 0;
	let tare = flt(row.tare_weight_kg) || 0;
	let count = cint(row.birds_count) || 0;
	let net = Math.max(0, gross - tare);

	frappe.model.set_value(cdt, cdn, "net_weight_kg", flt(net.toFixed(2)));

	if (row.is_weight_based_live_bird_sale) {
		if (net > 0) {
			frappe.model.set_value(cdt, cdn, "qty", flt(net.toFixed(2)));
		}
		if (count > 0 && net > 0) {
			frappe.model.set_value(cdt, cdn, "avg_bird_weight_kg", flt((net / count).toFixed(3)));
		} else {
			frappe.model.set_value(cdt, cdn, "avg_bird_weight_kg", 0);
		}
	}
}

function setup_customer_query(frm) {
	// Remove "Filtered by: is enabled and Company equals 'Poultry'."
	frm.set_query("customer", function () {
		return {
			query: "erpnext.controllers.queries.party_query",
		};
	});

	if (frm.fields_dict && frm.fields_dict.customer) {
		let df = frm.fields_dict.customer.df;
		delete df.link_filters;
		delete df.filters;
		delete df.filter_description;
	}
}

function setup_item_query(frm) {
	frm.set_query("item_code", "items", function () {
		return {
			query: "ob_poultry.poultry.api.item_query_by_place",
			filters: {
				place: "Poultry Sales Items",
			},
		};
	});
}

function hide_unwanted_fields(frm) {
	const fields = ["is_pos", "is_debit_note", "apply_tds"];
	fields.forEach((field) => {
		frm.toggle_display(field, false);
		frm.set_df_property(field, "hidden", 1);
	});
}

function fetch_and_display_egg_rates(frm) {
	frappe.call({
		method: "ob_poultry.poultry.api.get_egg_rate",
		args: {
			date: frm.doc.posting_date,
		},
		callback(r) {
			if (r.message && r.message.success) {
				frm.egg_rate_info = r.message;
				render_egg_rate_banner(frm, r.message);
			}
		},
	});
}

function render_egg_rate_banner(frm, info) {
	if (!info || !frm.fields_dict.items) return;

	let piece_str = flt(info.rate_per_piece).toFixed(2);
	let tray_str = flt(info.rate_per_tray).toFixed(2);
	let peti_str = flt(info.rate_per_peti).toFixed(2);
	let trend_icon = info.trend === "Up" ? "↑" : info.trend === "Down" ? "↓" : "→";

	let banner_html = `
		<div class="egg-rate-badge" style="margin-top: 6px; padding: 6px 12px; background: var(--bg-light-gray, #f8f9fa); border: 1px solid var(--border-color, #d1d8dd); border-radius: 6px; font-size: 12px; color: var(--text-color, #1f272e); display: flex; align-items: center; justify-content: space-between;">
			<div>
				<strong>🥚 NECC Egg Rate (${info.market}):</strong>
				₹${piece_str} / piece &bull; ₹${tray_str} / tray (30) &bull; ₹${peti_str} / peti (210)
				<span class="text-muted" style="margin-left: 8px;">Trend: ${trend_icon} ${
		info.trend || "Stable"
	}</span>
			</div>
			<div>
				<button type="button" class="btn btn-xs btn-default btn-apply-egg-rates" style="padding: 2px 8px; font-size: 11px;">
					Apply Rates to Egg Items
				</button>
			</div>
		</div>
	`;

	frm.set_df_property("items", "description", banner_html);

	setTimeout(() => {
		frm.$wrapper
			.find(".btn-apply-egg-rates")
			.off("click")
			.on("click", function () {
				apply_egg_rates_to_all_rows(frm);
			});
	}, 200);
}

function setup_egg_rate_actions(frm) {
	frm.add_custom_button(
		__("Fetch Today's Egg Rate"),
		function () {
			frappe.call({
				method: "ob_poultry.poultry.api.get_egg_rate",
				args: {
					date: frm.doc.posting_date,
				},
				freeze: true,
				freeze_message: __("Fetching NECC Egg Rates..."),
				callback(r) {
					if (r.message && r.message.success) {
						frm.egg_rate_info = r.message;
						render_egg_rate_banner(frm, r.message);
						show_egg_rate_dialog(frm, r.message);
					} else {
						frappe.msgprint(__("Could not retrieve egg rates at this time."));
					}
				},
			});
		},
		__("Poultry")
	);

	frm.add_custom_button(
		__("Apply Egg Rates to Items"),
		function () {
			apply_egg_rates_to_all_rows(frm);
		},
		__("Poultry")
	);
}

function show_egg_rate_dialog(frm, info) {
	let dialog = new frappe.ui.Dialog({
		title: __("NECC Egg Rates ({0})", [info.market]),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "rate_info_html",
				options: `
					<div style="font-size: 13px; line-height: 1.8;">
						<div><strong>Rate Date:</strong> ${info.rate_date}</div>
						<div><strong>Market:</strong> ${info.market}</div>
						<div><strong>Per Piece / Egg:</strong> ₹${flt(info.rate_per_piece).toFixed(2)}</div>
						<div><strong>Per Tray (30 Eggs):</strong> ₹${flt(info.rate_per_tray).toFixed(2)}</div>
						<div><strong>Per 100 Eggs:</strong> ₹${flt(info.rate_per_100).toFixed(2)}</div>
						<div><strong>Per Peti (210 Eggs):</strong> ₹${flt(info.rate_per_peti).toFixed(2)}</div>
						<div><strong>Trend:</strong> ${info.trend || "Stable"}</div>
					</div>
				`,
			},
		],
		primary_action_label: __("Apply to Egg Items"),
		primary_action() {
			apply_egg_rates_to_all_rows(frm);
			dialog.hide();
		},
	});
	dialog.show();
}

function is_egg_item(row) {
	if (!row.item_code) return false;
	let text = `${row.item_code} ${row.item_name || ""} ${row.item_group || ""}`.toLowerCase();
	return text.includes("egg");
}

function auto_apply_egg_rate_to_row(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (!row || !is_egg_item(row)) return;

	if (row.rate && flt(row.rate) > 0) return;

	let rate = get_rate_for_uom(frm, row.uom);
	if (rate > 0) {
		frappe.model.set_value(cdt, cdn, "rate", rate);
		frappe.show_alert(
			__("Applied NECC egg rate of ₹{0} based on UOM '{1}'", [rate, row.uom || "Nos"]),
			3
		);
	}
}

function apply_egg_rates_to_all_rows(frm) {
	if (!frm.egg_rate_info) {
		fetch_and_display_egg_rates(frm);
		frappe.msgprint(__("Fetching latest egg rates. Please retry in a moment."));
		return;
	}

	let updated_count = 0;
	(frm.doc.items || []).forEach((row) => {
		if (is_egg_item(row)) {
			let rate = get_rate_for_uom(frm, row.uom);
			if (rate > 0) {
				frappe.model.set_value(row.doctype, row.name, "rate", rate);
				updated_count++;
			}
		}
	});

	if (updated_count > 0) {
		frm.refresh_field("items");
		frappe.show_alert(__("Updated rates for {0} egg item(s)", [updated_count]), 4);
	} else {
		frappe.msgprint(__("No egg items found in the table to update."));
	}
}

function get_rate_for_uom(frm, uom) {
	if (!frm.egg_rate_info) return 0;
	let info = frm.egg_rate_info;
	let norm_uom = (uom || "").trim().toLowerCase();

	if (["tray", "trays"].includes(norm_uom)) {
		return flt(info.rate_per_tray);
	}
	if (["peti", "petis", "box", "boxes", "carton", "cartons"].includes(norm_uom)) {
		return flt(info.rate_per_peti);
	}
	if (["100", "hundred", "cent"].includes(norm_uom)) {
		return flt(info.rate_per_100);
	}
	return flt(info.rate_per_piece);
}
