frappe.ui.form.on("Poultry Batch", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status === "Active") {
			frm.add_custom_button(__("Close Batch"), () => {
				frappe.confirm(
					__("Close batch {0}? No further Daily Logs can be created against it afterward.", [frm.doc.name]),
					() => {
						frm.call({
							doc: frm.doc,
							method: "close_batch",
							freeze: true,
							callback: () => frm.reload_doc(),
						});
					}
				);
			});
		}

		if (!frm.is_new() && frm.doc.flock_source === "Contract" && frm.doc.growing_charge_scheme) {
			frm.add_custom_button(__("Calculate Growing Charge"), () => {
				frm.call({
					doc: frm.doc,
					method: "calculate_growing_charge",
					freeze: true,
					callback: (r) => {
						if (r.message !== undefined) {
							frappe.show_alert({
								message: __("Growing Charge: {0}", [format_currency(r.message)]),
								indicator: "green",
							});
						}
						frm.reload_doc();
					},
				});
			});
		}
	},
});
