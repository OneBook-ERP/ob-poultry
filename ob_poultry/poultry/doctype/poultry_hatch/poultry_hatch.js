// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Poultry Hatch", {
	onload(frm) {
		hide_record_navigation(frm);
	},

	refresh(frm) {
		hide_record_navigation(frm);
		setup_hatch_actions(frm);
		calculate_hatch_eggs(frm);
	},

	initial_egg_count(frm) {
		calculate_hatch_eggs(frm);
	},

	hatched_egg(frm) {
		calculate_hatch_eggs(frm);
	},

	move_to_stock(frm) {
		validate_remaining_allocation(frm, "move_to_stock");
	},

	wasted_eggs(frm) {
		validate_remaining_allocation(frm, "wasted_eggs");
	},
});

function hide_record_navigation(frm) {
	if (frm.page && frm.page.wrapper) {
		frm.page.wrapper.find(".prev-doc, .next-doc").hide();
	}

	if (!frm.hatch_nav_style_applied) {
		frappe.dom.set_style(`
			[data-page-route*="Poultry Hatch"] .prev-doc,
			[data-page-route*="Poultry Hatch"] .next-doc {
				display: none !important;
			}
		`);
		frm.hatch_nav_style_applied = true;
	}
}

function setup_hatch_actions(frm) {
	if (frm.is_new()) return;

	if (frm.doc.status !== "Closed" && !frm.doc.transferred_batch) {
		frm.add_custom_button(__("Chick Transfer"), () => {
			open_chick_transfer_dialog(frm);
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
		cint(frm.doc.hatched_egg) ||
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
				label: __("Hatched Chicks to Transfer"),
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

	// Style dialog primary action button with standard light button style (not black)
	let $primary_btn = dialog.get_primary_btn();
	if ($primary_btn) {
		$primary_btn.removeClass("btn-primary").addClass("btn-default");
	}
}

function calculate_hatch_eggs(frm) {
	const initial = cint(frm.doc.initial_egg_count);
	const has_hatched =
		frm.doc.hatched_egg !== undefined &&
		frm.doc.hatched_egg !== null &&
		frm.doc.hatched_egg !== "";
	const hatched = has_hatched ? cint(frm.doc.hatched_egg) : null;

	if (hatched === null) {
		if (frm.doc.remaining_eggs !== 0) {
			frm.set_value("remaining_eggs", 0);
		}
		render_remaining_eggs_summary(frm);
		return;
	}

	if (hatched < 0) {
		frappe.msgprint({
			title: __("Validation Warning"),
			indicator: "orange",
			message: __("Hatched Egg cannot be negative."),
		});
		frm.set_value("hatched_egg", 0);
		return;
	}

	if (initial > 0 && hatched > initial) {
		frappe.msgprint({
			title: __("Validation Warning"),
			indicator: "orange",
			message: __(
				"Hatched Egg ({0}) cannot exceed Initial Egg Count ({1}). Value has been reset to {1}.",
				[hatched, initial]
			),
		});
		frm.set_value("hatched_egg", initial);
		return;
	}

	const remaining = Math.max(0, initial - hatched);
	if (frm.doc.remaining_eggs !== remaining) {
		frm.set_value("remaining_eggs", remaining);
	}

	validate_remaining_allocation(frm);
	render_remaining_eggs_summary(frm);
}

function validate_remaining_allocation(frm, triggered_by) {
	const rem = cint(frm.doc.remaining_eggs);
	let move_stock = cint(frm.doc.move_to_stock || 0);
	let wasted = cint(frm.doc.wasted_eggs || 0);

	if (move_stock < 0) {
		frm.set_value("move_to_stock", 0);
		move_stock = 0;
	}
	if (wasted < 0) {
		frm.set_value("wasted_eggs", 0);
		wasted = 0;
	}

	if (triggered_by === "move_to_stock") {
		if (move_stock > rem) {
			frappe.show_alert(
				{
					message: __("Move to Stock ({0}) exceeds Remaining Eggs ({1})", [
						move_stock,
						rem,
					]),
					indicator: "orange",
				},
				5
			);
			frm.set_value("move_to_stock", rem);
			move_stock = rem;
		}
		if (move_stock + wasted > rem) {
			frm.set_value("wasted_eggs", Math.max(0, rem - move_stock));
			wasted = Math.max(0, rem - move_stock);
		}
	} else if (triggered_by === "wasted_eggs") {
		if (wasted > rem) {
			frappe.show_alert(
				{
					message: __("Wasted Eggs ({0}) exceeds Remaining Eggs ({1})", [wasted, rem]),
					indicator: "orange",
				},
				5
			);
			frm.set_value("wasted_eggs", rem);
			wasted = rem;
		}
		if (move_stock + wasted > rem) {
			frm.set_value("move_to_stock", Math.max(0, rem - wasted));
			move_stock = Math.max(0, rem - wasted);
		}
	} else {
		if (move_stock > rem) {
			frm.set_value("move_to_stock", rem);
			move_stock = rem;
		}
		if (move_stock + wasted > rem) {
			frm.set_value("wasted_eggs", Math.max(0, rem - move_stock));
			wasted = Math.max(0, rem - move_stock);
		}
	}

	render_remaining_eggs_summary(frm);
}

function render_remaining_eggs_summary(frm) {
	const has_hatched =
		frm.doc.hatched_egg !== undefined &&
		frm.doc.hatched_egg !== null &&
		frm.doc.hatched_egg !== "";
	if (!has_hatched) {
		if (frm.fields_dict.remaining_eggs) {
			frm.set_df_property("remaining_eggs", "description", "");
		}
		return;
	}

	const initial = cint(frm.doc.initial_egg_count);
	const hatched = cint(frm.doc.hatched_egg);
	const rem = Math.max(0, initial - hatched);
	const move_stock = cint(frm.doc.move_to_stock || 0);
	const wasted = cint(frm.doc.wasted_eggs || 0);
	const unallocated = Math.max(0, rem - (move_stock + wasted));

	const desc = __(
		"Total Unhatched: <b>{0}</b> | Move to Stock: <b>{1}</b> | Wasted: <b>{2}</b> | Unallocated: <b>{3}</b>",
		[
			rem.toLocaleString(),
			move_stock.toLocaleString(),
			wasted.toLocaleString(),
			unallocated.toLocaleString(),
		]
	);

	if (frm.fields_dict.remaining_eggs) {
		frm.set_df_property("remaining_eggs", "description", desc);
	}
	if (frm.fields_dict.move_to_stock) {
		frm.set_df_property("move_to_stock", "description", "");
	}
	if (frm.fields_dict.wasted_eggs) {
		frm.set_df_property("wasted_eggs", "description", "");
	}
}
