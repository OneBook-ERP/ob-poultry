frappe.ui.form.on("Poultry Feed Formula", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.ingredients && frm.doc.ingredients.length) {
			frm.add_custom_button(__(frm.doc.bom ? "Update BOM" : "Create BOM"), () => {
				frm.call({
					doc: frm.doc,
					method: "create_or_update_bom",
					freeze: true,
					callback: (r) => {
						if (r.message) {
							frappe.show_alert({
								message: __("BOM {0} ready", [r.message]),
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
