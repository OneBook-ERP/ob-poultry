frappe.ui.form.on("Poultry Batch", {
	refresh(frm) {
		setup_transfer_history_grid(frm);
		setup_daily_logs_history_grid(frm);
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

function setup_daily_logs_history_grid(frm) {
	if (!frm.fields_dict.daily_logs_history_html) return;

	if (frm.is_new()) {
		frm.fields_dict.daily_logs_history_html.$wrapper.html(`
			<div class="text-muted" style="padding: 16px; font-size: 13px; font-style: italic;">
				${__("Save the batch to view daily logs and sales history.")}
			</div>
		`);
		return;
	}

	frm.call({
		method: "ob_poultry.poultry.doctype.poultry_batch.poultry_batch.get_batch_daily_logs_and_sales",
		args: {
			batch_name: frm.doc.name,
		},
		callback(r) {
			const logs = r.message || [];
			render_daily_logs_history_table(frm, logs);
		},
	});
}

function render_daily_logs_history_table(frm, logs) {
	const $wrapper = frm.fields_dict.daily_logs_history_html.$wrapper;
	$wrapper.empty();

	if (!logs || logs.length === 0) {
		$wrapper.html(`
			<div class="text-center text-muted" style="padding: 24px 16px; border: 1px dashed var(--border-color); border-radius: 8px; margin: 8px 0;">
				<div style="font-size: 13px; font-weight: 500;">${__(
					"No Daily Logs or Sales recorded for this batch yet."
				)}</div>
				<div style="font-size: 11px; margin-top: 4px;">${__(
					"Daily logs created for this batch will automatically appear here."
				)}</div>
			</div>
		`);
		return;
	}

	frm.__daily_logs_state = {
		logs: logs,
		page: 1,
		page_size: 10,
	};

	render_paged_daily_logs(frm);
}

function render_paged_daily_logs(frm) {
	const $wrapper = frm.fields_dict.daily_logs_history_html.$wrapper;
	const state = frm.__daily_logs_state;
	const logs = state.logs;
	const page_size = state.page_size || 10;
	const total_pages = Math.max(1, Math.ceil(logs.length / page_size));
	const current_page = Math.min(Math.max(1, state.page), total_pages);
	state.page = current_page;

	const start_idx = (current_page - 1) * page_size;
	const end_idx = Math.min(start_idx + page_size, logs.length);
	const paged_logs = logs.slice(start_idx, end_idx);

	let rows_html = "";
	paged_logs.forEach((row, idx) => {
		const row_num = start_idx + idx + 1;
		const formatted_date = frappe.datetime.str_to_user(row.log_date);
		const day = row.day_of_week || "";
		const shed = row.shed || "-";
		const week_day = row.week_day || "-";
		const mortality = cint(row.mortality);
		const feed_kg = flt(row.feed_consumed_kg);
		const total_eggs = cint(row.total_eggs);
		const sales_amt = flt(row.total_sales_amount);

		const mortality_style =
			mortality > 0
				? "color: var(--red-500, #e02424); font-weight: 600;"
				: "color: var(--text-muted);";
		const sales_style =
			sales_amt > 0
				? "color: var(--green-600, #057a55); font-weight: 600;"
				: "color: var(--text-muted);";

		rows_html += `
			<div class="grid-row" data-index="${
				start_idx + idx
			}" style="border-bottom: 1px solid var(--table-border-color); cursor: pointer; transition: background-color 0.12s ease;">
				<div class="data-row row m-0" style="display: flex; align-items: center; min-height: 40px; padding: 6px 0;">
					<div class="row-index text-center" style="width: 44px; min-width: 44px; color: var(--text-muted); font-size: 12px;">
						<span>${row_num}</span>
					</div>
					<div class="col" style="flex: 1.3; font-weight: 500; color: var(--text-color); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
						${formatted_date}
						<span class="text-muted" style="font-size: 11px; margin-left: 3px;">(${day})</span>
					</div>
					<div class="col" style="flex: 1.2; font-size: 13px; color: var(--text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
						${frappe.utils.escape_html(shed)}
					</div>
					<div class="col" style="flex: 0.9; font-size: 12px;">
						<span class="badge badge-light" style="font-weight: 500; font-size: 11px;">${frappe.utils.escape_html(
							week_day
						)}</span>
					</div>
					<div class="col" style="flex: 1; text-align: right; font-size: 13px; ${mortality_style}">
						${mortality > 0 ? mortality.toLocaleString() : "0"}
					</div>
					<div class="col" style="flex: 1.1; text-align: right; font-size: 13px; color: var(--text-color);">
						${feed_kg > 0 ? feed_kg.toFixed(1) : "0.0"}
					</div>
					<div class="col" style="flex: 1.1; text-align: right; font-size: 13px; color: var(--text-color);">
						${total_eggs > 0 ? total_eggs.toLocaleString() : "0"}
					</div>
					<div class="col" style="flex: 1.3; text-align: right; font-size: 13px; ${sales_style}">
						${sales_amt > 0 ? format_currency(sales_amt) : "₹0.00"}
					</div>
					<div class="col text-center" style="width: 40px; min-width: 40px;">
						<span class="btn-open-row text-muted" title="${__(
							"View Log Details"
						)}" style="display: inline-block;">
							<svg class="icon icon-xs" style="width: 12px; height: 12px; stroke: currentColor;"><use href="#icon-chevron-right"></use></svg>
						</span>
					</div>
				</div>
			</div>
		`;
	});

	const has_prev = current_page > 1;
	const has_next = current_page < total_pages;

	const pagination_html = `
		<div class="grid-footer" style="padding: 8px 14px; background-color: var(--subtle-fg, #fafbfc); border-top: 1px solid var(--table-border-color); display: flex; justify-content: space-between; align-items: center;">
			<div class="text-muted" style="font-size: 12px;">
				${__("Showing {0} - {1} of {2} logs", [start_idx + 1, end_idx, logs.length])}
			</div>
			<div class="grid-pagination" style="display: flex; align-items: center; gap: 4px;">
				<button class="btn btn-secondary btn-xs btn-first-page" type="button" ${
					has_prev ? "" : "disabled"
				} style="padding: 2px 8px; font-size: 11px;">
					${__("First")}
				</button>
				<button class="btn btn-secondary btn-xs btn-prev-page" type="button" ${
					has_prev ? "" : "disabled"
				} style="padding: 2px 6px;">
					<svg class="icon icon-xs" style="width: 11px; height: 11px;"><use href="#icon-chevron-left"></use></svg>
				</button>
				<div class="page-text" style="display: inline-flex; align-items: center; gap: 4px; font-size: 12px; margin: 0 4px;">
					<span>${__("Page")}</span>
					<input class="current-page-number" type="number" min="1" max="${total_pages}" value="${current_page}" style="width: 42px; text-align: center; border: 1px solid var(--border-color); border-radius: 4px; padding: 1px 2px; font-size: 12px; height: 22px;">
					<span>${__("of {0}", [total_pages])}</span>
				</div>
				<button class="btn btn-secondary btn-xs btn-next-page" type="button" ${
					has_next ? "" : "disabled"
				} style="padding: 2px 6px;">
					<svg class="icon icon-xs" style="width: 11px; height: 11px;"><use href="#icon-chevron-right"></use></svg>
				</button>
				<button class="btn btn-secondary btn-xs btn-last-page" type="button" ${
					has_next ? "" : "disabled"
				} style="padding: 2px 8px; font-size: 11px;">
					${__("Last")}
				</button>
			</div>
		</div>
	`;

	const table_html = `
		<div class="frappe-control" style="margin: 8px 0;">
			<div class="form-grid" style="border: 1px solid var(--table-border-color); border-radius: var(--border-radius-md, 8px); overflow: hidden; background: var(--card-bg, #fff);">
				<div class="grid-heading-row" style="background-color: var(--subtle-fg, #fafbfc); border-bottom: 1px solid var(--table-border-color); color: var(--text-muted); font-size: 12px; font-weight: 600;">
					<div class="grid-row">
						<div class="data-row row m-0" style="display: flex; align-items: center; min-height: 34px; padding: 6px 0;">
							<div class="row-index text-center" style="width: 44px; min-width: 44px;">
								<span>#</span>
							</div>
							<div class="col" style="flex: 1.3;">${__("Date")}</div>
							<div class="col" style="flex: 1.2;">${__("Shed")}</div>
							<div class="col" style="flex: 0.9;">${__("Age")}</div>
							<div class="col" style="flex: 1; text-align: right;">${__("Mortality")}</div>
							<div class="col" style="flex: 1.1; text-align: right;">${__("Feed (kg)")}</div>
							<div class="col" style="flex: 1.1; text-align: right;">${__("Eggs")}</div>
							<div class="col" style="flex: 1.3; text-align: right;">${__("Sales (₹)")}</div>
							<div class="col text-center" style="width: 40px; min-width: 40px;"></div>
						</div>
					</div>
				</div>
				<div class="grid-body">
					<div class="rows">
						${rows_html}
					</div>
				</div>
				${pagination_html}
			</div>
		</div>
	`;

	$wrapper.html(table_html);

	$wrapper.find(".grid-body .grid-row").hover(
		function () {
			$(this).css("background-color", "var(--subtle-fg, #f8f9fa)");
		},
		function () {
			$(this).css("background-color", "transparent");
		}
	);

	$wrapper.find(".grid-body .grid-row").on("click", function (e) {
		e.preventDefault();
		const idx = parseInt($(this).attr("data-index"), 10);
		const row_data = logs[idx];
		if (row_data) {
			show_log_details_dialog(frm, row_data);
		}
	});

	$wrapper.find(".btn-first-page").on("click", function (e) {
		e.stopPropagation();
		state.page = 1;
		render_paged_daily_logs(frm);
	});

	$wrapper.find(".btn-prev-page").on("click", function (e) {
		e.stopPropagation();
		if (state.page > 1) {
			state.page -= 1;
			render_paged_daily_logs(frm);
		}
	});

	$wrapper.find(".btn-next-page").on("click", function (e) {
		e.stopPropagation();
		if (state.page < total_pages) {
			state.page += 1;
			render_paged_daily_logs(frm);
		}
	});

	$wrapper.find(".btn-last-page").on("click", function (e) {
		e.stopPropagation();
		state.page = total_pages;
		render_paged_daily_logs(frm);
	});

	$wrapper.find(".current-page-number").on("change keydown", function (e) {
		if (e.type === "keydown" && e.key !== "Enter") return;
		e.stopPropagation();
		const target_page = parseInt($(this).val(), 10);
		if (!isNaN(target_page) && target_page >= 1 && target_page <= total_pages) {
			state.page = target_page;
			render_paged_daily_logs(frm);
		}
	});
}

function show_log_details_dialog(frm, row) {
	const formatted_date = frappe.datetime.str_to_user(row.log_date);
	const title = __("Daily Log Details: {0} ({1})", [formatted_date, row.log_name]);

	let sales_html = "";
	if (row.sales && row.sales.length > 0) {
		let sales_rows = "";
		row.sales.forEach((s) => {
			sales_rows += `
				<tr style="border-bottom: 1px solid var(--border-color);">
					<td style="padding: 6px 10px;">${frappe.utils.escape_html(s.customer || "Walk-in Customer")}</td>
					<td style="padding: 6px 10px; text-align: right;">${cint(s.good_eggs).toLocaleString()} @ ₹${flt(
				s.table_egg_rate
			).toFixed(2)}</td>
					<td style="padding: 6px 10px; text-align: right;">${cint(s.broken_eggs).toLocaleString()} @ ₹${flt(
				s.broken_egg_rate
			).toFixed(2)}</td>
					<td style="padding: 6px 10px; text-align: right; font-weight: 600; color: var(--green-600, #057a55);">${format_currency(
						s.total_amount
					)}</td>
				</tr>
			`;
		});

		sales_html = `
			<table class="table table-bordered table-sm" style="width: 100%; margin-top: 6px; font-size: 12px; background: var(--card-bg, #fff);">
				<thead>
					<tr style="background-color: var(--table-header-bg, #f4f5f6); color: var(--text-muted);">
						<th style="padding: 6px 10px;">${__("Customer")}</th>
						<th style="padding: 6px 10px; text-align: right;">${__("Table Eggs")}</th>
						<th style="padding: 6px 10px; text-align: right;">${__("Broken Eggs")}</th>
						<th style="padding: 6px 10px; text-align: right;">${__("Total Amount")}</th>
					</tr>
				</thead>
				<tbody>
					${sales_rows}
				</tbody>
				<tfoot>
					<tr style="font-weight: 600; background: var(--table-header-bg, #f4f5f6);">
						<td colspan="3" style="padding: 6px 10px; text-align: right;">${__("Total Sales Amount:")}</td>
						<td style="padding: 6px 10px; text-align: right; color: var(--green-600, #057a55);">${format_currency(
							row.total_sales_amount
						)}</td>
					</tr>
				</tfoot>
			</table>
		`;
	} else {
		sales_html = `
			<div class="text-muted" style="padding: 10px 0; font-size: 12px; font-style: italic;">
				${__("No egg sales recorded on this daily log for this batch.")}
			</div>
		`;
	}

	const content_html = `
		<div class="log-details-modal" style="font-size: 13px; line-height: 1.5;">
			<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--border-color);">
				<div>
					<strong>${__("Shed")}:</strong> ${frappe.utils.escape_html(row.shed || "-")} &bull;
					<strong>${__("Age")}:</strong> ${frappe.utils.escape_html(row.week_day || "-")}
				</div>
				<button type="button" class="btn btn-xs btn-default btn-open-full-log" style="font-size: 11px;">
					${__("Open Full Daily Log ↗")}
				</button>
			</div>

			<!-- Row 1: Flock & Feed Cards -->
			<div class="row" style="margin-bottom: 12px;">
				<div class="col-sm-6">
					<div style="padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--fg-color, #fdfdfd); height: 100%;">
						<div style="font-weight: 600; margin-bottom: 6px; color: var(--text-color);">🐔 ${__(
							"Flock Metrics"
						)}</div>
						<div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
							<span class="text-muted">${__("Opening Birds")}:</span>
							<strong>${cint(row.opening_birds).toLocaleString()}</strong>
						</div>
						<div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
							<span class="text-muted">${__("Mortality")}:</span>
							<strong style="${row.mortality > 0 ? "color: var(--red-500, #e02424);" : ""}">${cint(
		row.mortality
	).toLocaleString()}</strong>
						</div>
						<div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
							<span class="text-muted">${__("Culled")}:</span>
							<strong>${cint(row.culled).toLocaleString()}</strong>
						</div>
						<div style="display: flex; justify-content: space-between; font-size: 12px; padding-top: 4px; border-top: 1px dashed var(--border-color);">
							<span class="text-muted">${__("Closing Birds")}:</span>
							<strong style="color: var(--primary);">${cint(row.closing_birds).toLocaleString()}</strong>
						</div>
					</div>
				</div>

				<div class="col-sm-6">
					<div style="padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--fg-color, #fdfdfd); height: 100%;">
						<div style="font-weight: 600; margin-bottom: 6px; color: var(--text-color);">🌾 ${__(
							"Feed Consumption"
						)}</div>
						<div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
							<span class="text-muted">${__("Feed Item")}:</span>
							<strong>${frappe.utils.escape_html(row.feed_item || "N/A")}</strong>
						</div>
						<div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
							<span class="text-muted">${__("Feed Spent")}:</span>
							<strong>${flt(row.feed_consumed_kg).toFixed(1)} kg</strong>
						</div>
						<div style="display: flex; justify-content: space-between; font-size: 12px; padding-top: 4px; border-top: 1px dashed var(--border-color);">
							<span class="text-muted">${__("Total Feed Cost")}:</span>
							<strong>${format_currency(row.feed_cost)}</strong>
						</div>
					</div>
				</div>
			</div>

			<!-- Row 2: Egg Production Card -->
			<div style="margin-bottom: 12px; padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--fg-color, #fdfdfd);">
				<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
					<span style="font-weight: 600; color: var(--text-color);">🥚 ${__("Egg Production")}</span>
					<span style="font-size: 12px; color: var(--text-muted);">${frappe.utils.escape_html(
						row.tray_summary || ""
					)}</span>
				</div>
				<div class="row" style="font-size: 12px;">
					<div class="col-xs-3">
						<span class="text-muted">${__("Total")}:</span> <strong>${cint(
		row.total_eggs
	).toLocaleString()}</strong>
					</div>
					<div class="col-xs-3">
						<span class="text-muted">${__("Table")}:</span> <strong>${cint(
		row.good_eggs
	).toLocaleString()}</strong>
					</div>
					<div class="col-xs-3">
						<span class="text-muted">${__("Broken")}:</span> <strong>${cint(
		row.broken_eggs
	).toLocaleString()}</strong>
					</div>
					<div class="col-xs-3">
						<span class="text-muted">${__("Laying %")}:</span> <strong>${flt(row.egg_production_pct).toFixed(
		1
	)}%</strong>
					</div>
				</div>
			</div>

			<!-- Row 3: Sales Card -->
			<div style="padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--fg-color, #fdfdfd);">
				<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
					<span style="font-weight: 600; color: var(--text-color);">💰 ${__("Sales Recorded")}</span>
					<span style="font-weight: 600; color: var(--green-600, #057a55);">${format_currency(
						row.total_sales_amount
					)}</span>
				</div>
				${sales_html}
			</div>
		</div>
	`;

	const dialog = new frappe.ui.Dialog({
		title: title,
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "details_html",
			},
		],
		primary_action_label: __("Close"),
		primary_action() {
			dialog.hide();
		},
	});

	dialog.show();
	dialog.fields_dict.details_html.$wrapper.html(content_html);

	const $primary_btn = dialog.get_primary_btn();
	if ($primary_btn) {
		$primary_btn.removeClass("btn-primary").addClass("btn-default");
	}

	dialog.$wrapper.find(".btn-open-full-log").on("click", function () {
		dialog.hide();
		frappe.set_route("Form", "Poultry Daily Log", row.log_name);
	});
}
