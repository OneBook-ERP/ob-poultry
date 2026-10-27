// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Poultry Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Sync Today's Egg Rate"), () => {
			frappe.call({
				method: "ob_poultry.poultry.utils.mkisan_api.fetch_and_store_egg_rates",
				args: {
					force: 1
				},
				freeze: true,
				freeze_message: __("Fetching today's NECC egg rate from MKisan..."),
				callback(r) {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __("Synced successfully: {0} @ ₹{1}/egg", [r.message.market, r.message.rate_per_piece]),
							indicator: "green"
						});
						frm.reload_doc();
					} else {
						frappe.msgprint({
							title: __("Sync Notice"),
							message: (r.message && r.message.message) || __("Unable to sync rate."),
							indicator: "orange"
						});
					}
				}
			});
		});
	}
});
