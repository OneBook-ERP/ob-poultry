// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Poultry Daily Egg Rate", {
	refresh(frm) {
		// Cleanly remove any old alert banner
		if (frm.set_intro) {
			frm.set_intro(null);
		}

		// Once a record is saved, lock rate_date and market to preserve ledger integrity
		if (!frm.is_new()) {
			frm.set_df_property("rate_date", "read_only", 1);
			frm.set_df_property("market", "read_only", 1);
		}

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

			// Clean, subtle text directly under the date field
			frm.set_df_property("rate_date", "description", badge_html);

			// Page indicator badge next to title
			frm.page.set_indicator(__("Live Synced"), "blue");
		}
	}
});
