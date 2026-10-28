// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Poultry Daily Egg Rate", {
	setup(frm) {
		frm.fetching_api = false;
	},

	refresh(frm) {
		// Cleanly remove any old alert banner
		if (frm.set_intro) {
			frm.set_intro(null);
		}

		// Once a record is saved, lock rate_date and market to preserve ledger integrity
		if (!frm.is_new()) {
			frm.set_df_property("rate_date", "read_only", 1);
			frm.set_df_property("market", "read_only", 1);
		} else {
			// On new document, if market is set but rates are empty, auto-fetch
			if (frm.doc.market && (!frm.doc.rate_per_piece || flt(frm.doc.rate_per_piece) === 0)) {
				auto_fetch_market_rate(frm);
			}
		}

		// Add "Fetch Rate from API" button
		frm.add_custom_button(__("Fetch Rate from API"), () => {
			auto_fetch_market_rate(frm, true);
		});

		update_sync_badge(frm);
	},

	market(frm) {
		// When market is chosen on a new record or updated, auto-pull the rates
		if (frm.doc.market) {
			auto_fetch_market_rate(frm, false);
		}
	},

	rate_date(frm) {
		if (frm.is_new() && frm.doc.market && frm.doc.rate_date) {
			auto_fetch_market_rate(frm, false);
		}
	},

	rate_per_piece(frm) {
		// Auto-calculate tray, 100 eggs, and peti when rate_per_piece is typed
		let piece_rate = flt(frm.doc.rate_per_piece) || 0;
		if (piece_rate > 0) {
			frappe.db.get_single_value("Poultry Settings", "eggs_per_tray").then(val => {
				let tray_size = flt(val) || 30;
				frm.set_value("rate_per_tray", piece_rate * tray_size);
				frm.set_value("rate_per_100", piece_rate * 100);
				frm.set_value("rate_per_peti", piece_rate * 210);
			});
		}
	}
});

function auto_fetch_market_rate(frm, show_alert = false) {
	if (!frm.doc.market || frm.fetching_api) return;
	frm.fetching_api = true;

	frappe.call({
		method: "ob_poultry.poultry.utils.mkisan_api.get_today_egg_rate",
		args: {
			market: frm.doc.market,
			date: frm.doc.rate_date || frappe.datetime.get_today()
		},
		freeze: show_alert,
		freeze_message: __("Fetching {0} NECC egg rate from API...", [frm.doc.market]),
		callback(r) {
			frm.fetching_api = false;
			if (r.message && r.message.success) {
				let d = r.message;
				frm.set_value("rate_per_piece", flt(d.rate_per_piece));
				frm.set_value("rate_per_tray", flt(d.rate_per_tray));
				frm.set_value("rate_per_100", flt(d.rate_per_100));
				if (d.rate_per_peti) {
					frm.set_value("rate_per_peti", flt(d.rate_per_peti));
				} else {
					frm.set_value("rate_per_peti", flt(d.rate_per_piece) * 210);
				}
				if (d.trend) {
					frm.set_value("trend", d.trend);
				}
				if (d.national_average) {
					frm.set_value("national_average", flt(d.national_average));
				}
				if (d.synced_at) {
					frm.set_value("synced_at", d.synced_at);
				} else {
					frm.set_value("synced_at", frappe.datetime.now_datetime());
				}
				frm.set_value("source", "MKisan NECC API");

				update_sync_badge(frm);

				frappe.show_alert({
					message: __("Loaded {0} rate: ₹{1}/egg (₹{2}/tray)", [d.market, flt(d.rate_per_piece).toFixed(2), flt(d.rate_per_tray).toFixed(2)]),
					indicator: "green"
				});
			} else if (show_alert) {
				frappe.msgprint({
					title: __("API Notice"),
					message: (r.message && r.message.message) || __("No rate found for {0}.", [frm.doc.market]),
					indicator: "orange"
				});
			}
		}
	});
}

function update_sync_badge(frm) {
	if (frm.doc.synced_at) {
		let fetched_time = "";
		if (window.moment) {
			fetched_time = moment(frm.doc.synced_at).format("DD MMM YYYY, hh:mm A");
		} else {
			fetched_time = (frm.doc.synced_at || "").split(".")[0];
		}

		let rate_date_str = "";
		if (frm.doc.rate_date && window.moment) {
			rate_date_str = moment(frm.doc.rate_date).format("DD MMM YYYY");
		} else {
			rate_date_str = frm.doc.rate_date || "";
		}

		let source_name = frm.doc.source || "MKisan NECC API";
		let badge_text = `Synced from ${source_name} • Rate Date: ${rate_date_str} • Fetched: ${fetched_time}`;
		let badge_html = `<div style="margin-top: 5px; font-size: 11px; color: var(--text-muted); font-weight: 500;">
			${badge_text}
		</div>`;

		frm.set_df_property("rate_date", "description", badge_html);
		frm.page.set_indicator(__("Live Synced"), "blue");
	}
}
