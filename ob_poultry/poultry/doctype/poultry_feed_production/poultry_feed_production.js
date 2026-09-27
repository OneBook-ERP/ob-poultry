frappe.ui.form.on("Poultry Feed Production", {
	refresh(frm) {
		if (!frm.is_new() && !frm.doc.work_order) {
			frm.add_custom_button(__("Create Work Order"), () => {
				frm.call({
					doc: frm.doc,
					method: "create_work_order",
					freeze: true,
					callback: (r) => {
						if (r.message) {
							frappe.show_alert({ message: __("Work Order {0} created", [r.message]), indicator: "green" });
						}
						frm.reload_doc();
					},
				});
			});
		}
	},
});
