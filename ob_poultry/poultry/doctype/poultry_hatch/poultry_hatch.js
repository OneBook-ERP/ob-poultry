// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Poultry Hatch", {
	refresh(frm) {
		setup_hatch_actions(frm);
	},
});

function setup_hatch_actions(frm) {
	if (frm.is_new()) return;

	if (frm.doc.status !== "Closed" && !frm.doc.transferred_batch) {
		let $btn = frm.add_custom_button(__("Chick Transfer"), () => {
			open_chick_transfer_dialog(frm);
		});
		$btn.removeClass("btn-primary")
			.addClass("btn-chick-transfer")
			.css({
				"background-color": "#1b64da",
				"border-color": "#1b64da",
				color: "#ffffff",
			})
			.on("mouseenter", function () {
				$(this).css({
					"background-color": "#1553b7",
					"border-color": "#1553b7",
					color: "#ffffff",
				});
			})
			.on("mouseleave", function () {
				$(this).css({
					"background-color": "#1b64da",
					"border-color": "#1b64da",
					color: "#ffffff",
				});
			});
	}

	if (frm.doc.transferred_batch) {
		frm.add_custom_button(
			__("View Batch ({0})", [frm.doc.transferred_batch]),
			() => {
				frappe.set_route("Form", "Poultry Batch", frm.doc.transferred_batch);
			},
			__("Actions")
		);
	}
}

function open_chick_transfer_dialog(frm) {
	let default_count =
		cint(frm.doc.initial_bird_count) ||
		cint(frm.doc.actual_chicks) ||
		cint(frm.doc.initial_egg_count) ||
		cint(frm.doc.eggs_set) ||
		0;

	let dialog = new frappe.ui.Dialog({
		title: __("Chick Transfer: {0}", [frm.doc.name]),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "shed",
				label: __("Shed to Transfer"),
				options: "Poultry Shed",
				reqd: 1,
				get_query: () => {
					return {
						filters: { is_active: 1 },
					};
				},
				onchange: () => {
					let shed_name = dialog.get_value("shed");
					if (shed_name) {
						frappe.db
							.get_value("Poultry Shed", shed_name, "default_feed_warehouse")
							.then((r) => {
								if (r.message && r.message.default_feed_warehouse) {
									dialog.set_value(
										"feed_warehouse",
										r.message.default_feed_warehouse
									);
								}
							});
					}
				},
			},
			{
				fieldtype: "Link",
				fieldname: "feed_warehouse",
				label: __("Feed Warehouse"),
				options: "Warehouse",
				description: __(
					"Feed warehouse to issue feed from for this batch (auto-filled from shed)"
				),
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Int",
				fieldname: "bird_count",
				label: __("Current Bird Count"),
				default: default_count,
				read_only: 1,
				description: __("Chicks from this hatch to transfer into the new batch"),
			},
		],
		primary_action_label: __("Transfer"),
		primary_action(values) {
			let bird_count =
				cint(values.bird_count) || cint(dialog.get_value("bird_count")) || default_count;

			if (!values.shed) {
				frappe.msgprint(__("Please select a destination Shed."));
				return;
			}
			if (bird_count <= 0) {
				frappe.msgprint(__("Bird count must be greater than 0."));
				return;
			}

			frappe.call({
				method: "ob_poultry.poultry.doctype.poultry_hatch.poultry_hatch.transfer_chicks",
				args: {
					hatch_name: frm.doc.name,
					shed: values.shed,
					feed_warehouse: values.feed_warehouse,
					bird_count: bird_count,
				},
				freeze: true,
				freeze_message: __("Transferring chicks and creating Batch..."),
				callback(r) {
					if (r.message) {
						dialog.hide();
						frm.reload_doc();
						frappe.show_alert(
							{
								message: __(
									"Successfully transferred {0} chicks to Batch {1} in Shed {2}",
									[r.message.count, r.message.batch, r.message.shed]
								),
								indicator: "green",
							},
							5
						);
						frappe.confirm(
							__(
								"Chicks transferred successfully! Do you want to open the new Batch <b>{0}</b> now?",
								[r.message.batch]
							),
							() => {
								frappe.set_route("Form", "Poultry Batch", r.message.batch);
							}
						);
					}
				},
			});
		},
	});

	dialog.show();

	// Style dialog primary action button with primary blue instead of black
	let $primary_btn = dialog.get_primary_btn();
	if ($primary_btn) {
		$primary_btn
			.removeClass("btn-primary")
			.addClass("btn-chick-transfer")
			.css({
				"background-color": "#1b64da",
				"border-color": "#1b64da",
				color: "#ffffff",
			})
			.on("mouseenter", function () {
				$(this).css({
					"background-color": "#1553b7",
					"border-color": "#1553b7",
					color: "#ffffff",
				});
			})
			.on("mouseleave", function () {
				$(this).css({
					"background-color": "#1b64da",
					"border-color": "#1b64da",
					color: "#ffffff",
				});
			});
	}
}
