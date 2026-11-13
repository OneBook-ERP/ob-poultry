frappe.ui.form.on("Poultry Feed Formula", {
	setup(frm) {
		frm.set_query("feed_item", () => {
			return {
				query: "ob_poultry.poultry.api.item_query_by_place",
				filters: {
					place: "Feed Items",
				},
			};
		});

		frm.set_query("raw_material", "ingredients", (doc, cdt, cdn) => {
			let row = locals[cdt][cdn];
			let place =
				row && row.category === "Medicine" ? "Medicines & Vaccines" : "Feed Raw Materials";
			return {
				query: "ob_poultry.poultry.api.item_query_by_place",
				filters: {
					place: place,
				},
			};
		});
	},

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
