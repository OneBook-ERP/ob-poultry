frappe.ui.form.on("Poultry Batch", {
	refresh(frm) {
		setup_transfer_history_grid(frm);
		setup_daily_logs_grid(frm);
		update_batch_week_ui(frm);
		handle_layer_sexed_counts_ui(frm);

		if (!frm.is_new()) {
			frm.set_df_property("breed", "read_only", 1);
			frm.set_df_property("initial_bird_count", "read_only", 1);
		}

		if (!frm.is_new() && frm.doc.status === "Active") {
			frm.add_custom_button(__("Close Batch"), () => {
				frappe.confirm(
					__(
						"Close batch {0}? No further Daily Logs can be created against it afterward.",
						[frm.doc.name]
					),
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

			frm.add_custom_button(__("Transfer Shed"), () => {
				frm.call({
					doc: frm.doc,
					method: "get_shed_summary",
					freeze: true,
					callback: function (r) {
						if (!r.message) return;
						const shed_counts = r.message.shed_counts || {};
						const available_sheds = Object.keys(shed_counts).filter(
							(s) => (shed_counts[s] || 0) > 0
						);

						if (available_sheds.length === 0) {
							frappe.msgprint(__("No birds available in any shed to transfer."));
							return;
						}

						const age_days = frm.doc.start_date
							? frappe.datetime.get_day_diff(
									frappe.datetime.get_today(),
									frm.doc.start_date
							  )
							: 0;
						const age_weeks = Math.floor(age_days / 7);

						let default_from = frm.doc.shed;
						if (!shed_counts[default_from]) {
							default_from = available_sheds[0];
						}

						check_and_open_transfer(
							frm,
							default_from,
							shed_counts[default_from] || frm.doc.current_bird_count || 0,
							age_weeks,
							age_days,
							shed_counts,
							false
						);
					},
				});
			});
		}

		if (
			!frm.is_new() &&
			frm.doc.flock_source === "Contract" &&
			frm.doc.growing_charge_scheme
		) {
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
	start_date(frm) {
		update_batch_week_ui(frm);
	},
	end_date(frm) {
		update_batch_week_ui(frm);
	},
	status(frm) {
		update_batch_week_ui(frm);
	},
	breed(frm) {
		if (frm.doc.breed) {
			frappe.db.get_value("Poultry Breed", frm.doc.breed, "breed_type", (r) => {
				if (r && r.breed_type) {
					frm.set_value("breed_type", r.breed_type);
					handle_layer_sexed_counts_ui(frm);
				}
			});
		}
	},
	breed_type(frm) {
		handle_layer_sexed_counts_ui(frm);
	},
	initial_bird_count(frm) {
		if (frm.doc.breed_type === "Layer") {
			frm.set_value("female_bird_count", frm.doc.initial_bird_count || 0);
			frm.set_value("male_bird_count", 0);
		}
	},
	female_bird_count(frm) {
		if (
			frm.doc.breed_type === "Layer" &&
			frm.doc.female_bird_count &&
			!frm.doc.initial_bird_count
		) {
			frm.set_value("initial_bird_count", frm.doc.female_bird_count);
		}
	},
});

frappe.ui.form.on("Poultry Batch Shed Transfer", {
	form_render(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row) return;
		const remaining = parseInt(row.remaining_birds, 10) || 0;
		const grid = frm.fields_dict.shed_transfers ? frm.fields_dict.shed_transfers.grid : null;
		const grid_row = grid && grid.grid_rows_by_docname ? grid.grid_rows_by_docname[cdn] : null;

		if (grid_row && grid_row.open_form) {
			const $form = grid_row.open_form.wrapper;
			$form.find(".transfer-remaining-row-action").remove();
			if (remaining > 0) {
				const $banner = $(`
					<div class="transfer-remaining-row-action" style="margin: 10px 0 15px 0; padding: 12px 16px; background-color: var(--fg-color, #f8f9fa); border: 1px solid var(--border-color); border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
						<div>
							<strong style="color: var(--text-color);">${remaining.toLocaleString()} birds</strong> still remain in <strong>${frappe.utils.escape_html(
					row.from_shed
				)}</strong>.
						</div>
						<button type="button" class="btn btn-xs btn-primary btn-modal-transfer-remaining" style="font-weight: 600;">
							↗ Transfer Remaining (${remaining.toLocaleString()})
						</button>
					</div>
				`);
				$form.prepend($banner);
				$banner.find(".btn-modal-transfer-remaining").on("click", function (e) {
					e.preventDefault();
					grid_row.toggle_view(false);
					handle_row_transfer_click(frm, row.from_shed, remaining);
				});
			}
		}
	},
});

frappe.ui.form.on("Poultry Batch Daily Log Entry", {
	form_render(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row) return;

		const grid = frm.fields_dict.daily_logs ? frm.fields_dict.daily_logs.grid : null;
		const grid_row = grid && grid.grid_rows_by_docname ? grid.grid_rows_by_docname[cdn] : null;

		if (grid_row) {
			const form_wrapper = grid_row.open_form
				? grid_row.open_form.wrapper
				: grid_row.grid_form
				? grid_row.grid_form.wrapper
				: null;
			if (form_wrapper) {
				form_wrapper.find(".btn-open-full-log-toolbar").remove();
				if (row.daily_log) {
					const $btn = $(`
						<button type="button" class="btn btn-xs btn-default btn-open-full-log-toolbar" style="margin-left: 10px; font-size: 11px;">
							${__("Open Full Daily Log ↗")}
						</button>
					`);
					$btn.on("click", function (e) {
						e.preventDefault();
						e.stopPropagation();
						frappe.set_route("Form", "Poultry Daily Log", row.daily_log);
					});
					form_wrapper.find(".grid-header-toolbar .panel-title").append($btn);
				}
			}
			const active_form = grid_row.grid_form || grid_row.open_form;
			if (
				active_form &&
				active_form.fields_dict &&
				active_form.fields_dict.sales_details_html
			) {
				active_form.fields_dict.sales_details_html.$wrapper.html(
					row.sales_details_html || ""
				);
			}
		}
	},
});

function setup_transfer_history_grid(frm) {
	if (!frm.fields_dict.shed_transfers || !frm.fields_dict.shed_transfers.grid) {
		return;
	}

	const grid = frm.fields_dict.shed_transfers.grid;
	const rem_field = grid.get_field("remaining_birds");
	if (rem_field) {
		rem_field.formatter = function (value, df, options, doc) {
			if (!doc) return value || 0;
			const remaining = value !== undefined && value !== null ? value : 0;
			if (remaining > 0) {
				return `<button type="button" class="btn btn-xs btn-primary btn-transfer-remaining-pill" data-from-shed="${frappe.utils.escape_html(
					doc.from_shed
				)}" data-remaining="${remaining}" title="${__(
					"Click to transfer remaining birds from {0}",
					[doc.from_shed]
				)}" style="padding: 2px 10px; font-weight: 600; cursor: pointer; white-space: nowrap; border-radius: 12px;">
					${remaining.toLocaleString()} &nbsp;↗ Transfer
				</button>`;
			} else {
				return `<span class="text-muted" style="font-weight: 500; font-size: 11px;">0 (Completed)</span>`;
			}
		};
		grid.refresh();
	}

	$(frm.wrapper)
		.off("click", ".btn-transfer-remaining-pill, [data-fieldname='remaining_birds']")
		.on(
			"click",
			".btn-transfer-remaining-pill, [data-fieldname='remaining_birds']",
			function (e) {
				e.preventDefault();
				e.stopPropagation();
				e.stopImmediatePropagation();

				let from_shed = $(this).attr("data-from-shed");
				let remaining = $(this).attr("data-remaining");

				if (!from_shed) {
					const row_name = $(this).closest(".grid-row").attr("data-name");
					const row = (frm.doc.shed_transfers || []).find((r) => r.name === row_name);
					if (row) {
						from_shed = row.from_shed;
						remaining = row.remaining_birds;
					}
				}

				if (!from_shed) return;
				remaining = parseInt(remaining, 10) || 0;
				handle_row_transfer_click(frm, from_shed, remaining);
			}
		);
}

function handle_row_transfer_click(frm, from_shed, remaining) {
	if (remaining <= 0) {
		frappe.msgprint(__("All birds from shed {0} have already been transferred.", [from_shed]));
		return;
	}

	const age_days = frm.doc.start_date
		? frappe.datetime.get_day_diff(frappe.datetime.get_today(), frm.doc.start_date)
		: 0;
	const age_weeks = Math.floor(age_days / 7);

	check_and_open_transfer(frm, from_shed, remaining, age_weeks, age_days, null, true);
}

function check_and_open_transfer(
	frm,
	from_shed,
	available_birds,
	age_weeks,
	age_days,
	shed_counts,
	locked_source = false
) {
	if (age_weeks < 16) {
		frappe.confirm(
			__(
				"The flock age is only {0} weeks ({1} days). Standard transfer is typically at 16–18 weeks. Are you sure you want to transfer sheds now?",
				[age_weeks, age_days]
			),
			() => {
				show_transfer_dialog(
					frm,
					from_shed,
					available_birds,
					age_weeks,
					age_days,
					shed_counts,
					locked_source
				);
			}
		);
	} else {
		show_transfer_dialog(
			frm,
			from_shed,
			available_birds,
			age_weeks,
			age_days,
			shed_counts,
			locked_source
		);
	}
}

function show_transfer_dialog(
	frm,
	from_shed,
	available_birds,
	age_weeks,
	age_days,
	shed_counts,
	locked_source = false
) {
	from_shed = from_shed || frm.doc.shed;
	if (available_birds === undefined || available_birds === null) {
		available_birds = frm.doc.current_bird_count || 0;
	}

	const sheds_with_birds = shed_counts
		? Object.keys(shed_counts).filter((s) => shed_counts[s] > 0)
		: [from_shed];

	const d = new frappe.ui.Dialog({
		title: __("Transfer Shed"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "info_html",
				options: `
					<div style="margin-bottom: 15px; font-size: 13px; line-height: 1.8; color: var(--text-color);">
						<div><strong>Source Shed:</strong> <span class="lbl-source-shed">${frappe.utils.escape_html(
							from_shed
						)}</span></div>
						<div><strong>Remaining Birds in Source Shed:</strong> <span class="lbl-remaining-birds">${available_birds.toLocaleString()}</span> birds</div>
						<div><strong>Flock Age:</strong> ${age_weeks} Weeks (${age_days} Days)</div>
					</div>
				`,
			},
			{
				label: __("From Shed (Source)"),
				fieldname: "from_shed",
				fieldtype: locked_source || sheds_with_birds.length <= 1 ? "Link" : "Select",
				options:
					locked_source || sheds_with_birds.length <= 1
						? "Poultry Shed"
						: sheds_with_birds.map((s) => ({
								label: `${s} (${(
									shed_counts[s] || 0
								).toLocaleString()} birds remaining)`,
								value: s,
						  })),
				default: from_shed,
				read_only: locked_source || sheds_with_birds.length <= 1 ? 1 : 0,
				reqd: 1,
				onchange: function () {
					if (!locked_source && shed_counts) {
						const selected_shed = d.get_value("from_shed");
						const new_avail = shed_counts[selected_shed] || 0;
						d.$wrapper.find(".lbl-source-shed").text(selected_shed);
						d.$wrapper.find(".lbl-remaining-birds").text(new_avail.toLocaleString());
						d.set_value("birds_to_transfer", new_avail);
						d.set_df_property(
							"birds_to_transfer",
							"description",
							__("Number of birds to move from {0} (Max: {1})", [
								selected_shed,
								new_avail.toLocaleString(),
							])
						);
					}
				},
			},
			{
				label: __("New Destination Shed"),
				fieldname: "new_shed",
				fieldtype: "Link",
				options: "Poultry Shed",
				reqd: 1,
				get_query: () => {
					const curr_source = d.get_value("from_shed") || from_shed;
					return {
						filters: {
							is_active: 1,
							name: ["!=", curr_source],
						},
					};
				},
			},
			{
				label: __("Transfer Date"),
				fieldname: "transfer_date",
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
			{
				label: __("Birds to Transfer"),
				fieldname: "birds_to_transfer",
				fieldtype: "Int",
				default: available_birds,
				reqd: 1,
				description: __("Number of birds to move from {0} (Max: {1})", [
					from_shed,
					available_birds.toLocaleString(),
				]),
			},
			{
				label: __("Transit Mortality (Birds)"),
				fieldname: "transit_mortality",
				fieldtype: "Int",
				default: 0,
				description: __("Birds lost or culled during transit/handling"),
			},
			{
				label: __("Notes"),
				fieldname: "notes",
				fieldtype: "Small Text",
			},
		],
		primary_action_label: __("Confirm Transfer"),
		primary_action: function (values) {
			const sel_source = values.from_shed || from_shed;
			const max_allowed =
				shed_counts && shed_counts[sel_source] !== undefined
					? shed_counts[sel_source]
					: available_birds;

			const birds_to_transfer = parseInt(values.birds_to_transfer, 10);
			const transit = parseInt(values.transit_mortality, 10) || 0;

			if (!birds_to_transfer || birds_to_transfer <= 0) {
				frappe.msgprint(__("Number of birds to transfer must be greater than 0."));
				return;
			}

			if (birds_to_transfer > max_allowed) {
				frappe.msgprint(
					__(
						"Number of birds to transfer ({0}) cannot be greater than remaining birds in {1} ({2}).",
						[
							birds_to_transfer.toLocaleString(),
							sel_source,
							max_allowed.toLocaleString(),
						]
					)
				);
				return;
			}

			if (transit < 0) {
				frappe.msgprint(__("Transit mortality cannot be negative."));
				return;
			}

			if (transit > birds_to_transfer) {
				frappe.msgprint(
					__("Transit mortality ({0}) cannot exceed birds to transfer ({1}).", [
						transit,
						birds_to_transfer.toLocaleString(),
					])
				);
				return;
			}

			const birds_to_place = birds_to_transfer - transit;
			frappe.confirm(
				__(
					"Are you sure you want to transfer {0} birds from {1} to {2}? (Transit mortality: {3}, Birds placed: {4})",
					[
						birds_to_transfer.toLocaleString(),
						sel_source,
						values.new_shed,
						transit,
						birds_to_place.toLocaleString(),
					]
				),
				() => {
					d.hide();
					frm.call({
						doc: frm.doc,
						method: "transfer_shed",
						args: {
							from_shed: sel_source,
							new_shed: values.new_shed,
							transfer_date: values.transfer_date,
							birds_to_transfer: birds_to_transfer,
							transit_mortality: transit,
							notes: values.notes || "",
						},
						freeze: true,
						freeze_message: __("Transferring flock..."),
						callback: function (r) {
							if (!r.exc) {
								frm.reload_doc();
							}
						},
					});
				}
			);
		},
	});
	d.show();
}

function update_batch_week_ui(frm) {
	if (!frm.doc.start_date) {
		frm.set_value("batch_week", 0);
		return;
	}
	const ref_date =
		frm.doc.status === "Closed" && frm.doc.end_date
			? frm.doc.end_date
			: frappe.datetime.get_today();
	const age_days = frappe.datetime.get_day_diff(ref_date, frm.doc.start_date);
	const age_weeks = Math.max(0, Math.floor(age_days / 7));

	if (frm.doc.batch_week !== age_weeks) {
		frm.set_value("batch_week", age_weeks);
	}
	if (frm.fields_dict.batch_week) {
		frm.set_df_property(
			"batch_week",
			"description",
			__("Flock age: {0} weeks ({1} days)", [age_weeks, age_days])
		);
	}
}

function handle_layer_sexed_counts_ui(frm) {
	const is_layer = frm.doc.breed_type === "Layer";
	frm.toggle_display("male_bird_count", !is_layer);

	if (is_layer) {
		frm.set_df_property(
			"section_break_batch_sexed",
			"description",
			__(
				"Layer flocks consist entirely of female birds. Female bird count is synchronized with initial bird count."
			)
		);
		if (frm.doc.male_bird_count) {
			frm.set_value("male_bird_count", 0);
		}
		if (
			frm.doc.initial_bird_count &&
			frm.doc.female_bird_count !== frm.doc.initial_bird_count
		) {
			frm.set_value("female_bird_count", frm.doc.initial_bird_count);
		}
	} else {
		frm.set_df_property(
			"section_break_batch_sexed",
			"description",
			__(
				"Optional breakdown for breeder/mixed flocks; initial_bird_count remains the total."
			)
		);
	}
}

function setup_daily_logs_grid(frm) {
	if (!frm.fields_dict.daily_logs || !frm.fields_dict.daily_logs.grid) {
		return;
	}

	const grid = frm.fields_dict.daily_logs.grid;
	grid.cannot_add_rows = true;
	grid.wrapper.find(".grid-add-row").hide();
	grid.wrapper.find(".grid-remove-rows").hide();
	grid.wrapper.find(".grid-remove-all-rows").hide();

	if (grid.grid_pagination) {
		grid.grid_pagination.page_length = 10;
	}

	const mort_field = grid.get_field("mortality");
	if (mort_field) {
		mort_field.formatter = function (value) {
			const val = cint(value);
			if (val > 0) {
				return `<span style="color: var(--red-500, #e02424); font-weight: 600;">${val.toLocaleString()}</span>`;
			}
			return `<span class="text-muted">0</span>`;
		};
	}

	const sales_field = grid.get_field("total_sales_amount");
	if (sales_field) {
		sales_field.formatter = function (value) {
			const val = flt(value);
			if (val > 0) {
				return `<span style="color: var(--green-600, #057a55); font-weight: 600;">${format_currency(
					val
				)}</span>`;
			}
			return `<span class="text-muted">₹0.00</span>`;
		};
	}

	const age_field = grid.get_field("week_day");
	if (age_field) {
		age_field.formatter = function (value) {
			if (!value) return "-";
			return `<span class="badge badge-light" style="font-weight: 500; font-size: 11px;">${frappe.utils.escape_html(
				value
			)}</span>`;
		};
	}

	const date_field = grid.get_field("log_date");
	if (date_field) {
		date_field.formatter = function (value, df, options, doc) {
			if (!value) return "-";
			const formatted = frappe.datetime.str_to_user(value);
			const day =
				doc && doc.day_of_week
					? ` <span class="text-muted" style="font-size: 11px;">(${frappe.utils.escape_html(
							doc.day_of_week
					  )})</span>`
					: "";
			return `<span>${formatted}${day}</span>`;
		};
	}

	grid.wrapper
		.off("click", ".grid-row .data-row")
		.on("click", ".grid-row .data-row", function (e) {
			if ($(e.target).closest("a, input, button, .grid-row-check, .btn-open-row").length) {
				return;
			}
			const row_name = $(this).closest(".grid-row").attr("data-name");
			const grid_row = grid.grid_rows_by_docname
				? grid.grid_rows_by_docname[row_name]
				: null;
			if (grid_row) {
				grid_row.toggle_view();
			}
		});

	if (!frm.is_new() && (!frm.doc.daily_logs || frm.doc.daily_logs.length === 0)) {
		frm.call({
			doc: frm.doc,
			method: "load_daily_logs_history",
			callback: function (r) {
				if (r.message) {
					frm.doc.daily_logs = r.message;
					frm.refresh_field("daily_logs");
					if (grid.grid_pagination) {
						grid.grid_pagination.page_length = 10;
						grid.grid_pagination.update_page_numbers();
					}
				}
			},
		});
	}
}
