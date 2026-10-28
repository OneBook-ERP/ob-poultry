// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Poultry Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Sync Today's Egg Rate"), () => {
			let btn = frm.page.get_inner_group_button(__("Sync Today's Egg Rate"));
			if (btn) btn.prop("disabled", true);

			frappe.call({
				method: "ob_poultry.poultry.utils.mkisan_api.fetch_and_store_egg_rates",
				args: {
					force: 1,
				},
				freeze: true,
				freeze_message: __("Checking NECC egg rate from MKisan API..."),
				callback(r) {
					if (btn) btn.prop("disabled", false);
					if (r.message && r.message.success) {
						if (r.message.already_updated) {
							frappe.show_alert({
								message: r.message.message,
								indicator: "blue",
							});
						} else {
							frappe.show_alert({
								message: __("Synced successfully: {0} @ ₹{1}/egg", [
									r.message.market,
									flt(r.message.rate_per_piece).toFixed(2),
								]),
								indicator: "green",
							});
							frm.reload_doc();
						}
					} else {
						frappe.msgprint({
							title: __("Sync Notice"),
							message:
								(r.message && r.message.message) || __("Unable to sync rate."),
							indicator: "orange",
						});
					}
				},
			});
		});
	},
});
