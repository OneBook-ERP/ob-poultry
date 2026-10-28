// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Poultry Daily Egg Rate", {
	refresh(frm) {
		// Cleanly remove any old alert banner
		if (frm.set_intro) {
			frm.set_intro(null);
		}

		if (frm.doc.synced_at) {
			let formatted_time = "";
			if (window.moment) {
				formatted_time = moment(frm.doc.synced_at).format("DD MMM YYYY, hh:mm A");
			} else {
				formatted_time = (frm.doc.synced_at || "").split(".")[0];
			}

			let source_name = frm.doc.source || "MKisan NECC API";
			let badge_text = `Synced from ${source_name} • Updated: ${formatted_time}`;
			let badge_html = `<div style="margin-top: 5px; font-size: 11px; color: var(--text-muted); font-weight: 500;">
				${badge_text}
			</div>`;

			// Clean, subtle text directly under the date field (no green banner)
			frm.set_df_property("rate_date", "description", badge_html);

			// Page indicator badge next to title
			frm.page.set_indicator(__("Live Synced"), "blue");
		}
	}
});
