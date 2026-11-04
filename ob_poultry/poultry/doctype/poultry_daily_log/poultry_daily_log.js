// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Poultry Daily Log", {
	setup(frm) {
		// Warehouse query: active warehouses only
		frm.set_query("warehouse", "feed_entries", function () {
			return {
				filters: {
					is_group: 0,
				},
			};
		});

		// Feed item query: filtered by Poultry Settings item group mapping
		frm.set_query("feed_item", "feed_entries", function () {
			return {
				query: "ob_poultry.poultry.api.item_query_by_place",
				filters: {
					place: "Feed Items",
				},
			};
		});

		if (frm.fields_dict.feed_item) {
			frm.set_query("feed_item", function () {
				return {
					query: "ob_poultry.poultry.api.item_query_by_place",
					filters: {
						place: "Feed Items",
					},
				};
			});
		}

		// Global styles for strict 3-tier view separation & shed child table
		frappe.dom.set_style(`
			/* Level 2: Shed List View - strictly show shed list, strictly hide data entry sections */
			.pdl-view-sheds [data-fieldname="section_break_sheds"],
			.pdl-view-sheds [data-fieldname="shed_entries"] {
				display: block !important;
			}
			.pdl-view-sheds [data-fieldname="section_break_shed_info"],
			.pdl-view-sheds [data-fieldname="section_break_eggs"],
			.pdl-view-sheds [data-fieldname="section_break_feeds"],
			.pdl-view-sheds [data-fieldname="section_break_flock"],
			.pdl-view-sheds [data-fieldname="section_break_sales"],
			.pdl-view-sheds [data-fieldname="section_break_notes"] {
				display: none !important;
			}

			/* Level 3: Data Entry View - strictly hide shed list, strictly show data entry sections */
			.pdl-view-entry [data-fieldname="section_break_sheds"],
			.pdl-view-entry [data-fieldname="shed_entries"] {
				display: none !important;
			}
			.pdl-view-entry [data-fieldname="section_break_shed_info"],
			.pdl-view-entry [data-fieldname="section_break_eggs"],
			.pdl-view-entry [data-fieldname="section_break_feeds"],
			.pdl-view-entry [data-fieldname="section_break_flock"],
			.pdl-view-entry [data-fieldname="section_break_sales"],
			.pdl-view-entry [data-fieldname="section_break_notes"] {
				display: block !important;
			}

			/* Native Shed Child Table row pointer & styling */
			[data-fieldname="shed_entries"] .grid-row {
				cursor: pointer !important;
			}
			[data-fieldname="shed_entries"] .grid-row:hover .data-row {
				background-color: var(--highlight-color, #f4f5f7) !important;
			}
			[data-fieldname="shed_entries"] .grid-footer {
				display: none !important;
			}

			/* Completely hide and suppress form-in-grid (Editing Row popup) on Shed table */
			[data-fieldname="shed_entries"] .form-in-grid,
			[data-fieldname="shed_entries"] .grid-form-heading,
			[data-fieldname="shed_entries"] .grid-form-body,
			[data-fieldname="shed_entries"] .grid-header-toolbar,
			[data-fieldname="shed_entries"] .btn-open-row,
			[data-fieldname="shed_entries"] .col:last-child a,
			[data-fieldname="shed_entries"] .col:last-child svg {
				display: none !important;
				visibility: hidden !important;
				height: 0 !important;
				max-height: 0 !important;
				padding: 0 !important;
				margin: 0 !important;
				overflow: hidden !important;
				pointer-events: none !important;
			}

			/* Dynamic toggle for Average Body Weight column in Flock Entries */
			.hide-pdl-weight [data-fieldname="flock_entries"] [data-fieldname="average_body_weight_g"],
			.hide-pdl-weight [data-fieldname="flock_entries"] .grid-static-col[data-fieldname="average_body_weight_g"],
			.hide-pdl-weight [data-fieldname="flock_entries"] .col[data-fieldname="average_body_weight_g"] {
				display: none !important;
			}

			/* Vertical Column Totals Row Styling */
			.grid-totals-row {
				background-color: var(--subtle-accent-background, #f8fafc) !important;
				border-top: 1px solid var(--border-color, #d1d8dd) !important;
				border-bottom: 1px solid var(--border-color, #d1d8dd) !important;
				font-weight: 700 !important;
			}
			.grid-totals-row .col {
				display: flex;
				align-items: center;
				min-height: 34px;
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
			}

			/* Hide Status indicator pill in Form header */
			.page-head .indicator-pill,
			.form-head .indicator-pill,
			.indicator-pill-round {
				display: none !important;
			}

			/* Remove pen / edit symbol in the 4 child tables */
			[data-fieldname="egg_entries"] .btn-open-row,
			[data-fieldname="feed_entries"] .btn-open-row,
			[data-fieldname="flock_entries"] .btn-open-row,
			[data-fieldname="sales_entries"] .btn-open-row,
			[data-fieldname="egg_entries"] .grid-body .grid-row .col:last-child a,
			[data-fieldname="feed_entries"] .grid-body .grid-row .col:last-child a,
			[data-fieldname="flock_entries"] .grid-body .grid-row .col:last-child a,
			[data-fieldname="sales_entries"] .grid-body .grid-row .col:last-child a,
			[data-fieldname="egg_entries"] .grid-body .grid-row .col:last-child svg,
			[data-fieldname="feed_entries"] .grid-body .grid-row .col:last-child svg,
			[data-fieldname="flock_entries"] .grid-body .grid-row .col:last-child svg,
			[data-fieldname="sales_entries"] .grid-body .grid-row .col:last-child svg {
				display: none !important;
				visibility: hidden !important;
				pointer-events: none !important;
			}
			[data-fieldname="sales_entries"] .grid-body .grid-row .col:last-child {
				pointer-events: none !important;
				cursor: default !important;
			}
			[data-fieldname="sales_entries"] .grid-footer,
			[data-fieldname="sales_entries"] .grid-add-row,
			[data-fieldname="sales_entries"] .grid-remove-rows,
			[data-fieldname="sales_entries"] .grid-remove-all-rows {
				display: none !important;
			}
		`);

		// Setup popstate listener to handle browser Back & Forward across all 3 levels
		if (!window.__pdl_popstate_installed) {
			window.__pdl_popstate_installed = true;
			window.addEventListener("popstate", function () {
				if (!cur_frm || cur_frm.doctype !== "Poultry Daily Log") return;
				cur_frm.events.sync_view_from_url(cur_frm);
			});
		}
	},

	refresh(frm) {
		// Close any open grid row forms immediately
		frappe.ui.form.close_grid_form();
		$(".form-in-grid").remove();

		// Prevent layout from auto-focusing on table rows (which triggers Editing Row popup)
		if (frm.layout && !frm.layout.__pdl_focus_patched) {
			frm.layout.__pdl_focus_patched = true;
			let orig_set_focus = frm.layout.set_focus;
			frm.layout.set_focus = function (field) {
				if (
					field &&
					field.df &&
					(field.df.fieldtype === "Table" || field.df.fieldname === "shed_entries")
				) {
					return false;
				}
				return orig_set_focus ? orig_set_focus.apply(this, arguments) : false;
			};
		}

		// Clean up any legacy back buttons
		frm.page && frm.page.wrapper.find("button:contains('Back to Sheds')").remove();
		$(frm.wrapper).find(".back-to-sheds, .btn-back-to-sheds").remove();

		// Set today's date for new records
		if (frm.is_new() && !frm.doc.log_date) {
			frm.set_value("log_date", frappe.datetime.get_today());
		}

		// Ensure Record Bird Weight Today is NOT ticked by default on new records
		if (frm.is_new() && !frm.doc.record_weight) {
			frm.set_value("record_weight", 0);
			frm.set_value("average_body_weight_g", 0);
		}

		// Ensure active sheds are populated
		frm.events.ensure_shed_entries(frm);

		// Cache Poultry Batch names for display in child tables
		frm.events.cache_batch_names(frm);

		// Synchronize Level 2 (Shed Data) vs Level 3 (Data Entry) based on URL query parameter (?shed=...)
		frm.events.sync_view_from_url(frm);
		frm.events.setup_child_grids(frm);

		frm.trigger("toggle_weight_field");
		frm.trigger("calculate_all_totals");

		frm.add_custom_button(__("Benchmark Check"), function () {
			frm.events.show_benchmark_comparison_dialog(frm);
		});
	},

	sync_view_from_url(frm) {
		let params = new URLSearchParams(window.location.search);
		let url_shed = params.get("shed");
		if (url_shed) {
			frm.events.show_data_entry_view(frm, decodeURIComponent(url_shed), false);
		} else {
			frm.events.show_shed_list_view(frm, false);
		}
	},

	show_shed_list_view(frm, push_history = false) {
		frm.doc.selected_shed = "";
		frm.selected_shed = "";

		// Manage browser history cleanly
		if (push_history) {
			history.pushState({ pdl_shed: "" }, "", window.location.pathname);
		}

		// Toggle CSS view classes on form wrapper
		$(frm.wrapper).removeClass("pdl-view-entry").addClass("pdl-view-sheds");
		if (frm.page && frm.page.wrapper) {
			$(frm.page.wrapper).removeClass("pdl-view-entry").addClass("pdl-view-sheds");
		}

		if (
			frm.fields_dict.benchmark_variance_html &&
			frm.fields_dict.benchmark_variance_html.$wrapper
		) {
			frm.fields_dict.benchmark_variance_html.$wrapper.empty();
		}

		// Direct element toggle for bulletproof separation
		let sec_sheds = frm.fields_dict.section_break_sheds;
		if (sec_sheds && sec_sheds.wrapper) {
			$(sec_sheds.wrapper)
				.removeClass("empty-section hide-control")
				.addClass("visible-section")
				.show();
			$(sec_sheds.wrapper).find(".section-body").show();
		}
		let shed_table = frm.fields_dict.shed_entries;
		if (shed_table && shed_table.wrapper) {
			$(shed_table.wrapper).removeClass("hide-control").show();
		}

		// Explicitly hide data entry sections
		[
			"section_break_shed_info",
			"section_break_eggs",
			"section_break_feeds",
			"section_break_flock",
			"section_break_sales",
			"section_break_notes",
		].forEach(function (sec_name) {
			let sec = frm.fields_dict[sec_name];
			if (sec && sec.wrapper) {
				$(sec.wrapper).hide();
			}
		});

		// Clear secondary action in page header
		frm.page.clear_secondary_action && frm.page.clear_secondary_action();

		// Update Breadcrumbs: 1st Poultry Daily Log, 2nd Shed Data
		frm.events.update_breadcrumbs(frm, null);

		// Refresh shed grid and bind row clicks
		if (shed_table && shed_table.grid) {
			shed_table.grid.refresh();
		}
		frm.events.setup_shed_grid(frm);
		frm.events.render_table_totals(frm, "shed_entries");
	},

	show_data_entry_view(frm, shed_name, push_history = true) {
		if (!shed_name) return;
		frm.doc.selected_shed = shed_name;
		frm.selected_shed = shed_name;

		// Manage browser history cleanly
		if (push_history) {
			let new_url = window.location.pathname + "?shed=" + encodeURIComponent(shed_name);
			history.pushState({ pdl_shed: shed_name }, "", new_url);
		}

		// Immediately close/destroy any open modal dialog
		cur_dialog && cur_dialog.hide && cur_dialog.hide();
		$(".modal:visible, .modal-backdrop").remove();
		$("body").removeClass("modal-open");

		// Toggle CSS view classes on form wrapper
		$(frm.wrapper).removeClass("pdl-view-sheds").addClass("pdl-view-entry");
		if (frm.page && frm.page.wrapper) {
			$(frm.page.wrapper).removeClass("pdl-view-sheds").addClass("pdl-view-entry");
		}

		// Explicitly HIDE shed list section & table
		let sec_sheds = frm.fields_dict.section_break_sheds;
		if (sec_sheds && sec_sheds.wrapper) {
			$(sec_sheds.wrapper).hide();
		}
		let shed_table = frm.fields_dict.shed_entries;
		if (shed_table && shed_table.wrapper) {
			$(shed_table.wrapper).hide();
		}

		// Explicitly SHOW data entry sections
		[
			"section_break_shed_info",
			"section_break_eggs",
			"section_break_feeds",
			"section_break_flock",
			"section_break_sales",
			"section_break_notes",
		].forEach(function (sec_name) {
			let sec = frm.fields_dict[sec_name];
			if (sec && sec.wrapper) {
				$(sec.wrapper)
					.removeClass("empty-section hide-control")
					.addClass("visible-section")
					.show();
				$(sec.wrapper).find(".section-body").show();
			}
		});

		// Refresh child grids inside now-visible sections
		["egg_entries", "feed_entries", "flock_entries", "sales_entries"].forEach(function (
			f_name
		) {
			let f = frm.fields_dict[f_name];
			if (f && f.grid) {
				f.grid.refresh();
			}
		});

		// Update Breadcrumbs: 1st Poultry Daily Log, 2nd Shed Data, 3rd Current Shed
		frm.events.update_breadcrumbs(frm, shed_name);

		// Add secondary action in toolbar for Back to Shed List
		frm.page.set_secondary_action(__("← Back to Shed List"), function () {
			frm.events.return_to_shed_list_clicked(frm);
		});

		// Render shed header nav bar with Previous / Next shed buttons
		frm.events.render_shed_header_nav(frm, shed_name);

		// Prevent clicking on breed link from navigating away to master
		if (frm.fields_dict.breed && frm.fields_dict.breed.$wrapper) {
			frm.fields_dict.breed.$wrapper
				.find("a")
				.off("click.pdl_stop")
				.on("click.pdl_stop", function (e) {
					e.preventDefault();
				})
				.css("pointer-events", "none");
		}

		// Filter child tables strictly to the active shed's batches
		frm.events.filter_tables_by_shed(frm, shed_name);
		frm.events.setup_child_grids(frm);

		// Render vertical totals on all data entry tables
		frm.events.render_all_table_totals(frm);

		// Load context for shed
		frm.trigger("load_shed_context");
	},

	return_to_shed_list_clicked(frm) {
		frm.events.show_shed_list_view(frm, true);
	},

	ensure_shed_entries(frm) {
		// If submitted and shed entries exist, do not mutate
		if (frm.doc.docstatus === 1 && frm.doc.shed_entries && frm.doc.shed_entries.length) {
			frm.events.setup_shed_grid(frm);
			frm.events.render_table_totals(frm, "shed_entries");
			return;
		}

		frappe.call({
			method: "ob_poultry.poultry.doctype.poultry_daily_log.poultry_daily_log.get_active_sheds",
			callback: function (r) {
				if (r.message && r.message.length) {
					let active_sheds = r.message;
					let existing_map = {};
					(frm.doc.shed_entries || []).forEach((row) => {
						if (row.shed) existing_map[row.shed] = row;
					});

					let changed = false;
					active_sheds.forEach((s) => {
						let shed_id = s.name || s.shed_name;
						let row = existing_map[shed_id];
						if (row) {
							if (
								row.batches_count !== s.active_batches_count ||
								row.total_birds !== s.total_birds
							) {
								row.batches_count = s.active_batches_count;
								row.total_birds = s.total_birds;
								changed = true;
							}
						} else {
							frm.add_child("shed_entries", {
								shed: shed_id,
								batches_count: s.active_batches_count || 1,
								total_birds: s.total_birds || 0,
								breed: s.breeds || "-",
							});
							changed = true;
						}
					});

					if (changed || !frm.doc.shed_entries || !frm.doc.shed_entries.length) {
						frm.refresh_field("shed_entries");
					}
					frm.events.setup_shed_grid(frm);
					frm.events.render_table_totals(frm, "shed_entries");
				}
			},
		});
	},

	setup_child_grids(frm) {
		// Ensure batch column formatters show Batch Name across all tables
		[
			"Poultry Daily Log Egg Entry",
			"Poultry Daily Log Feed Entry",
			"Poultry Daily Log Flock Entry",
			"Poultry Daily Log Sales Entry",
		].forEach(function (dt) {
			if (frappe.meta.docfield_map[dt] && frappe.meta.docfield_map[dt]["batch"]) {
				frappe.meta.docfield_map[dt]["batch"].formatter = function (
					value,
					df,
					options,
					doc
				) {
					if (!value) return "";
					if (frm.__batch_name_map && frm.__batch_name_map[value])
						return frm.__batch_name_map[value];
					if (window.__pdl_batch_names && window.__pdl_batch_names[value])
						return window.__pdl_batch_names[value];
					let m = value.match(/PB-\d+-0*(\d+)/i);
					return m ? "Batch " + m[1] : value;
				};
			}
		});

		["egg_entries", "feed_entries", "flock_entries"].forEach(function (fieldname) {
			let field = frm.fields_dict[fieldname];
			if (!field || !field.grid) return;

			let grid = field.grid;
			grid.meta.editable_grid = 1;

			let lock_rows = function () {
				if (!grid.grid_rows) return;
				grid.grid_rows.forEach(function (row) {
					row.open_form_button && row.open_form_button.hide();
					row.wrapper &&
						row.wrapper
							.find(".btn-open-row, .col:last-child a, .col:last-child svg")
							.hide();
					row.toggle_view = function () {
						return false;
					};
					row.open_form = function () {
						return false;
					};
				});
				frm.events.format_batch_cells(frm);
			};

			lock_rows();
			grid.wrapper
				.off("grid-row-render.pdl_no_dialog")
				.on("grid-row-render.pdl_no_dialog", function () {
					lock_rows();
				});
		});

		// Sales entries: fetched only, not editable, no row addition, remove pen symbol
		let sales_field = frm.fields_dict.sales_entries;
		if (sales_field && sales_field.grid) {
			let grid = sales_field.grid;
			grid.meta.editable_grid = 0;
			grid.cannot_add_rows = true;
			grid.wrapper
				.find(".grid-add-row, .grid-remove-rows, .grid-remove-all-rows, .grid-footer")
				.hide();
			$(sales_field.wrapper)
				.find(".grid-add-row, .grid-remove-rows, .grid-remove-all-rows, .grid-footer")
				.hide();

			let lock_sales_rows = function () {
				if (!grid.grid_rows) return;
				grid.grid_rows.forEach(function (row) {
					row.open_form_button && row.open_form_button.hide();
					row.wrapper
						.find(".btn-open-row, .col:last-child a, .col:last-child svg")
						.hide()
						.remove();
					row.toggle_view = function () {
						return false;
					};
					row.open_form = function () {
						return false;
					};
				});
				frm.events.format_batch_cells(frm);
			};
			lock_sales_rows();
			grid.wrapper
				.off("grid-row-render.pdl_no_pen")
				.on("grid-row-render.pdl_no_pen", function () {
					lock_sales_rows();
				});
		}

		frm.events.format_batch_cells(frm);
		frm.events.toggle_weight_field(frm);
	},

	cache_batch_names(frm) {
		window.__pdl_batch_names = window.__pdl_batch_names || {};
		frm.__batch_name_map = frm.__batch_name_map || {};

		frappe.db
			.get_list("Poultry Batch", {
				fields: ["name", "shed"],
				order_by: "name asc",
				limit: 100,
			})
			.then(function (batches) {
				if (!batches) return;
				let shed_batch_count = {};
				batches.forEach(function (b) {
					shed_batch_count[b.shed] = (shed_batch_count[b.shed] || 0) + 1;
					let name = "Batch " + shed_batch_count[b.shed];
					window.__pdl_batch_names[b.name] = name;
					frm.__batch_name_map[b.name] = name;
				});
				frm.events.format_batch_cells(frm);
			});
	},

	format_batch_cells(frm) {
		["egg_entries", "feed_entries", "flock_entries", "sales_entries"].forEach(function (
			fieldname
		) {
			let f = frm.fields_dict[fieldname];
			if (!f || !f.grid || !f.grid.grid_rows) return;
			f.grid.grid_rows.forEach(function (grid_row) {
				if (!grid_row.doc || !grid_row.doc.batch) return;
				let b_val = grid_row.doc.batch;
				let b_name =
					(frm.__batch_name_map && frm.__batch_name_map[b_val]) ||
					(window.__pdl_batch_names && window.__pdl_batch_names[b_val]) ||
					grid_row.doc.batch_name;
				if (!b_name) {
					let m = b_val.match(/PB-\d+-0*(\d+)/i);
					b_name = m ? "Batch " + m[1] : b_val;
				}
				let $batch_col = grid_row.wrapper.find('[data-fieldname="batch"]');
				if ($batch_col.length) {
					let $link = $batch_col.find("a");
					if ($link.length) {
						$link.text(b_name);
					} else {
						let $static = $batch_col.find(".static-area");
						if ($static.length) {
							$static.text(b_name);
						} else {
							$batch_col.text(b_name);
						}
					}
				}
			});
		});
	},

	setup_shed_grid(frm) {
		let field = frm.fields_dict.shed_entries;
		if (!field || !field.grid) return;

		let grid = field.grid;
		grid.cannot_add_rows = true;
		grid.wrapper
			.find(".grid-add-row, .grid-remove-rows, .grid-remove-all-rows, .grid-footer")
			.hide();

		// Disable grid-level toggle_view and open_form so Editing Row popup never triggers
		grid.toggle_view = function () {
			return false;
		};
		grid.open_form = function () {
			return false;
		};
		grid.show_form = function () {
			return false;
		};

		let lock_shed_rows = function () {
			if (!grid.grid_rows) return;
			grid.grid_rows.forEach(function (row) {
				row.open_form_button && row.open_form_button.hide();
				row.wrapper
					.find(".btn-open-row, .col:last-child a, .col:last-child svg")
					.hide()
					.remove();
				row.wrapper.find(".form-in-grid").remove();
				row.toggle_view = function () {
					return false;
				};
				row.open_form = function () {
					return false;
				};
				row.show_form = function () {
					return false;
				};

				// Intercept row click at the lowest DOM level (data-row)
				row.wrapper
					.find(".data-row")
					.off("click.pdl_nav")
					.on("click.pdl_nav", function (e) {
						if (
							$(e.target).hasClass("grid-row-check") ||
							$(e.target).closest(".grid-row-check").length
						)
							return;
						e.preventDefault();
						e.stopPropagation();
						frappe.ui.form.close_grid_form();
						$(".form-in-grid").remove();

						let shed =
							(row.doc && row.doc.shed) ||
							$(this).find('[data-fieldname="shed"]').text().trim();
						if (shed) {
							frm.events.show_data_entry_view(frm, shed, true);
						}
						return false;
					});
			});
		};

		lock_shed_rows();
		grid.wrapper
			.off("grid-row-render.pdl_shed_lock")
			.on("grid-row-render.pdl_shed_lock", function () {
				lock_shed_rows();
			});

		// Also handle delegated clicks on grid wrapper
		field.$wrapper
			.off("click.pdl_nav")
			.on("click.pdl_nav", ".grid-row:not(.grid-totals-row)", function (e) {
				if (
					$(e.target).hasClass("grid-row-check") ||
					$(e.target).closest(".grid-row-check").length
				)
					return;
				e.preventDefault();
				e.stopPropagation();
				frappe.ui.form.close_grid_form();
				$(".form-in-grid").remove();

				let docname = $(this).attr("data-name");
				let row_doc = (frm.doc.shed_entries || []).find((r) => r.name === docname);
				let shed =
					(row_doc && row_doc.shed) ||
					$(this).find('[data-fieldname="shed"]').text().trim();
				if (shed) {
					frm.events.show_data_entry_view(frm, shed, true);
				}
				return false;
			});
	},

	update_breadcrumbs(frm, in_shed) {
		if (!frm.page || !frm.page.set_breadcrumbs) return;

		let items = [
			{
				label: __("Poultry Daily Log"),
				href: "/desk/poultry-daily-log",
			},
		];

		if (in_shed) {
			// Level 2: Shed Data (clickable to return to Level 2 shed list)
			items.push({
				label: __(frm.doc.name || "Shed Data"),
				onclick: function () {
					frm.events.return_to_shed_list_clicked(frm);
				},
			});
			// Level 3: Current Shed Data Entry
			items.push({
				label: in_shed,
			});
		} else {
			// Level 2: Current Log (Shed List view)
			items.push({
				label: __(frm.doc.name || "Shed Data"),
			});
		}

		frm.page.set_breadcrumbs(items);
	},

	render_shed_header_nav(frm, shed_name) {
		let sec = frm.fields_dict.section_break_shed_info;
		if (!sec || !sec.wrapper) return;

		let sec_body = sec.wrapper.find(".section-body");
		sec_body.find(".shed-nav-bar").remove();

		// Find list of available sheds for Prev / Next switching
		let sheds = [];
		(frm.doc.shed_entries || []).forEach((r) => {
			if (r.shed && !sheds.includes(r.shed)) sheds.push(r.shed);
		});

		let cur_idx = sheds.indexOf(shed_name);
		let prev_shed = cur_idx > 0 ? sheds[cur_idx - 1] : null;
		let next_shed = cur_idx >= 0 && cur_idx < sheds.length - 1 ? sheds[cur_idx + 1] : null;

		let prev_btn = prev_shed
			? `
			<button type="button" class="btn btn-xs btn-default btn-prev-shed" title="Go to ${frappe.utils.escape_html(
				prev_shed
			)}">
				Previous Shed
			</button>
		`
			: "";

		let next_btn = next_shed
			? `
			<button type="button" class="btn btn-xs btn-default btn-next-shed" title="Go to ${frappe.utils.escape_html(
				next_shed
			)}">
				Next Shed
			</button>
		`
			: "";

		let nav_html = `
			<div class="shed-nav-bar col-12 d-flex justify-content-between align-items-center mb-3 p-2 border rounded bg-white">
				<div class="d-flex align-items-center">
					<span class="font-weight-bold" style="font-size: 14px;">${frappe.utils.escape_html(
						shed_name
					)}</span>
				</div>
				<div class="d-flex gap-2">
					${prev_btn}
					${next_btn}
				</div>
			</div>
		`;

		sec_body.prepend(nav_html);

		if (prev_shed) {
			sec_body.find(".btn-prev-shed").on("click", function () {
				frm.events.show_data_entry_view(frm, prev_shed, true);
			});
		}
		if (next_shed) {
			sec_body.find(".btn-next-shed").on("click", function () {
				frm.events.show_data_entry_view(frm, next_shed, true);
			});
		}
	},

	load_shed_context(frm) {
		if (!frm.doc.selected_shed) return;

		frappe.call({
			method: "ob_poultry.poultry.doctype.poultry_daily_log.poultry_daily_log.get_shed_context",
			args: {
				shed: frm.doc.selected_shed,
				log_date: frm.doc.log_date || frappe.datetime.get_today(),
			},
			callback: function (r) {
				if (!r.message) return;
				let ctx = r.message;

				// Read-only Shed Info fields
				frm.set_value("shed_name", ctx.shed_name || frm.doc.selected_shed);
				frm.set_value("breed", ctx.breed || "");
				frm.set_value("sex", ctx.sex || "");

				let batches = ctx.batches || [];
				let shed = frm.doc.selected_shed;

				window.__pdl_batch_names = window.__pdl_batch_names || {};
				frm.__batch_name_map = frm.__batch_name_map || {};
				batches.forEach(function (b, idx) {
					let name = b.batch_name || "Batch " + (idx + 1);
					window.__pdl_batch_names[b.batch] = name;
					frm.__batch_name_map[b.batch] = name;
				});

				// Only auto-add child rows if in draft mode
				if (frm.doc.docstatus === 0) {
					batches.forEach(function (b) {
						// 1. Eggs Table
						let egg_exists = (frm.doc.egg_entries || []).some(
							(row) => (row.shed === shed || !row.shed) && row.batch === b.batch
						);
						if (!egg_exists) {
							frm.add_child("egg_entries", {
								shed: shed,
								batch: b.batch,
								week_day: b.week_day,
								in_stock: b.opening_eggs || 0,
								good_eggs: 0,
								double_yolk_eggs: 0,
								broken_eggs: 0,
								waste_eggs: 0,
							});
						}

						// 2. Feeds Table
						let feed_exists = (frm.doc.feed_entries || []).some(
							(row) => (row.shed === shed || !row.shed) && row.batch === b.batch
						);
						if (!feed_exists) {
							frm.add_child("feed_entries", {
								shed: shed,
								batch: b.batch,
								week_day: b.week_day,
								warehouse: b.feed_warehouse || "",
								feed_item: b.feed_item || "",
								opening_stock_kg: b.opening_stock_kg || 0,
								feed_spent_kg: 0,
								feed_spent_g_per_bird: 0,
								currently_available_kg: b.opening_stock_kg || 0,
								rate_per_kg: b.rate_per_kg || 0,
								total_feed_cost: 0,
							});
						}

						// 3. Chickens Table
						let flock_exists = (frm.doc.flock_entries || []).some(
							(row) => (row.shed === shed || !row.shed) && row.batch === b.batch
						);
						if (!flock_exists) {
							frm.add_child("flock_entries", {
								shed: shed,
								batch: b.batch,
								week_day: b.week_day,
								opening_birds: b.opening_birds || 0,
								dead: 0,
								culled: 0,
								closing_birds: b.opening_birds || 0,
							});
						}

						// 4. Sales Table
						let sales_exists = (frm.doc.sales_entries || []).some(
							(row) => (row.shed === shed || !row.shed) && row.batch === b.batch
						);
						if (!sales_exists) {
							frm.add_child("sales_entries", {
								shed: shed,
								batch: b.batch,
								week_day: b.week_day,
								good_eggs: 0,
								table_egg_rate: 0,
								table_egg_amount: 0,
								broken_eggs: 0,
								broken_egg_rate: 0,
								broken_egg_amount: 0,
								double_yolk_eggs: 0,
								rate: 0,
								total_amount: 0,
							});
						}
					});

					frm.refresh_field("egg_entries");
					frm.refresh_field("feed_entries");
					frm.refresh_field("flock_entries");
					frm.refresh_field("sales_entries");
				}

				frm.__current_shed_context = ctx;
				frm.events.filter_tables_by_shed(frm, shed);
				frm.trigger("calculate_all_totals");
				frm.events.render_all_table_totals(frm);
				frm.events.format_batch_cells(frm);
				frm.events.toggle_weight_field(frm);
				frm.events.render_benchmark_variance_card(frm);
			},
		});
	},

	render_benchmark_variance_card(frm) {
		// Card removed from daily log form per user request; health check is displayed as a popup while saving or via action button.
		if (
			frm.fields_dict.benchmark_variance_html &&
			frm.fields_dict.benchmark_variance_html.$wrapper
		) {
			frm.fields_dict.benchmark_variance_html.$wrapper.empty();
		}
	},

	show_benchmark_comparison_dialog(frm, on_proceed) {
		let shed =
			frm.doc.selected_shed ||
			(frm.doc.shed_entries && frm.doc.shed_entries.length
				? frm.doc.shed_entries[0].shed
				: null);
		if (!frm.__current_shed_context && shed) {
			frappe.call({
				method: "ob_poultry.poultry.doctype.poultry_daily_log.poultry_daily_log.get_shed_context",
				args: {
					log_date: frm.doc.log_date || frappe.datetime.nowdate(),
					shed: shed,
				},
				callback: function (r) {
					frm.__current_shed_context = r.message || {};
					frm.events.render_benchmark_dialog_content(frm, on_proceed);
				},
				error: function () {
					if (typeof on_proceed === "function") {
						on_proceed();
					}
				},
			});
			return;
		}
		frm.events.render_benchmark_dialog_content(frm, on_proceed);
	},

	render_benchmark_dialog_content(frm, on_proceed) {
		let ctx = frm.__current_shed_context || {};
		let batches = ctx.batches || [];
		let cur_shed = frm.doc.selected_shed;
		let record_wt = cint(frm.doc.record_weight) === 1;

		let warnings = [];

		batches.forEach(function (b, idx) {
			let bmk = b.benchmark || {};
			let std_wt = flt(bmk.standard_body_weight_g) || 0;
			let std_hdep = flt(bmk.standard_hdep_pct) || 0;
			let std_mort = flt(bmk.standard_mortality_pct) || 0;
			let std_feed = flt(bmk.standard_feed_per_bird_g) || 0;

			let batch_name = b.batch_name || `Batch ${idx + 1}`;
			let batch_label = `${batch_name}${b.week_day ? " (" + b.week_day + ")" : ""}`;

			// Find matching child rows for this batch
			let f_row = (frm.doc.flock_entries || []).find((r) => r.batch === b.batch) || {};
			let e_row = (frm.doc.egg_entries || []).find((r) => r.batch === b.batch) || {};
			let feed_row = (frm.doc.feed_entries || []).find((r) => r.batch === b.batch) || {};

			let birds = flt(f_row.opening_birds) || flt(b.opening_birds) || 0;
			let dead = flt(f_row.dead) || 0;
			let eggs = flt(e_row.total_eggs) || 0;
			let feed_spent = flt(feed_row.feed_spent_kg) || 0;

			// 1. Avg Body Weight (evaluated per batch if record_weight is enabled)
			if (record_wt) {
				let act_wt = flt(f_row.average_body_weight_g) || 0;
				if (act_wt > 0 && std_wt > 0) {
					let dev = ((act_wt - std_wt) / std_wt) * 100;
					if (dev <= -10) {
						warnings.push({
							batch: batch_label,
							metric: __("Avg Body Weight"),
							actual: `${act_wt.toLocaleString()} g`,
							standard: `${std_wt.toLocaleString()} g`,
							variance: dev.toFixed(1) + "%",
							issue: __("Underweight ({0})", [Math.abs(dev).toFixed(1) + "%"]),
							type: "danger",
						});
					} else if (dev >= 10) {
						warnings.push({
							batch: batch_label,
							metric: __("Avg Body Weight"),
							actual: `${act_wt.toLocaleString()} g`,
							standard: `${std_wt.toLocaleString()} g`,
							variance: "+" + dev.toFixed(1) + "%",
							issue: __("Overweight (+{0})", [dev.toFixed(1) + "%"]),
							type: "warning",
						});
					}
				}
			}

			// 2. Egg Production (HDEP %)
			if (std_hdep > 0 && birds > 0) {
				let act_hdep = (eggs / birds) * 100;
				let dev = ((act_hdep - std_hdep) / std_hdep) * 100;
				if (dev <= -10) {
					warnings.push({
						batch: batch_label,
						metric: __("Egg Production (HDEP)"),
						actual: `${act_hdep.toFixed(1)}% (${eggs.toLocaleString()} eggs)`,
						standard: `${std_hdep.toFixed(1)}%`,
						variance: dev.toFixed(1) + "%",
						issue: __("Low Yield ({0})", [Math.abs(dev).toFixed(1) + "%"]),
						type: "danger",
					});
				}
			}

			// 3. Daily Mortality
			if (birds > 0 && dead > 0) {
				let act_mort = (dead / birds) * 100;
				if (std_mort > 0) {
					let dev = ((act_mort - std_mort) / std_mort) * 100;
					if (dev >= 10) {
						warnings.push({
							batch: batch_label,
							metric: __("Daily Mortality"),
							actual: `${act_mort.toFixed(2)}% (${dead} dead)`,
							standard: `${std_mort.toFixed(2)}%`,
							variance: "+" + dev.toFixed(1) + "%",
							issue: __("High Mortality (+{0})", [dev.toFixed(1) + "%"]),
							type: "danger",
						});
					}
				} else if (act_mort >= 0.1) {
					warnings.push({
						batch: batch_label,
						metric: __("Daily Mortality"),
						actual: `${act_mort.toFixed(2)}% (${dead} dead)`,
						standard: "≤ 0.05%",
						variance: "> normal",
						issue: __("High Mortality ({0} dead)", [dead]),
						type: "danger",
					});
				}
			}

			// 4. Feed Intake
			if (std_feed > 0 && birds > 0 && feed_spent > 0) {
				let act_feed_g = (feed_spent * 1000) / birds;
				let dev = ((act_feed_g - std_feed) / std_feed) * 100;
				if (dev <= -15) {
					warnings.push({
						batch: batch_label,
						metric: __("Feed Intake / Bird"),
						actual: `${act_feed_g.toFixed(1)} g`,
						standard: `${std_feed.toFixed(1)} g`,
						variance: dev.toFixed(1) + "%",
						issue: __("Under-consumption ({0})", [Math.abs(dev).toFixed(1) + "%"]),
						type: "warning",
					});
				} else if (dev >= 15) {
					warnings.push({
						batch: batch_label,
						metric: __("Feed Intake / Bird"),
						actual: `${act_feed_g.toFixed(1)} g`,
						standard: `${std_feed.toFixed(1)} g`,
						variance: "+" + dev.toFixed(1) + "%",
						issue: __("Over-consumption (+{0})", [dev.toFixed(1) + "%"]),
						type: "warning",
					});
				}
			}
		});

		let is_on_save = typeof on_proceed === "function";

		// If saving and no warnings exist, smoothly proceed without interrupting
		if (is_on_save && warnings.length === 0) {
			on_proceed();
			return;
		}

		let d = new frappe.ui.Dialog({
			title:
				warnings.length > 0
					? __("Benchmark Warnings Check{0}", [cur_shed ? ": " + cur_shed : ""])
					: __("Benchmark Check{0}", [cur_shed ? ": " + cur_shed : ""]),
			size: "large",
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "modal_html",
				},
			],
			primary_action_label: is_on_save ? __("Proceed & Save") : __("Close"),
			primary_action() {
				d.hide();
				if (is_on_save) {
					on_proceed();
				}
			},
		});

		if (is_on_save) {
			d.set_secondary_action_label(__("Review / Edit Log"));
			d.set_secondary_action(() => {
				d.hide();
			});
		}

		let modal_content = "";
		if (warnings.length > 0) {
			modal_content = `
			<div>
				<p class="text-muted small mb-2">
					${__("Only metrics that failed standard breed benchmark tolerances are listed below:")}
				</p>
				<div class="table-responsive border rounded" style="overflow: hidden;">
					<table class="table table-bordered table-hover table-sm m-0">
						<thead style="background-color: var(--subtle-accent-background, #f8fafc); border-bottom: 1px solid var(--border-color, #d1d8dd);">
							<tr>
								<th style="padding: 8px 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 11px;">${__(
									"Batch"
								)}</th>
								<th style="padding: 8px 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 11px;">${__(
									"Metric"
								)}</th>
								<th style="padding: 8px 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 11px; text-align: right;">${__(
									"Actual Value"
								)}</th>
								<th style="padding: 8px 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 11px; text-align: right;">${__(
									"Standard Benchmark"
								)}</th>
								<th style="padding: 8px 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 11px; text-align: right;">${__(
									"Variance %"
								)}</th>
								<th style="padding: 8px 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 11px;">${__(
									"Warning Condition"
								)}</th>
							</tr>
						</thead>
						<tbody>
							${warnings
								.map(
									(w) => `
								<tr>
									<td style="padding: 8px 10px; font-weight: 600;">${frappe.utils.escape_html(w.batch)}</td>
									<td style="padding: 8px 10px;">${frappe.utils.escape_html(w.metric)}</td>
									<td style="padding: 8px 10px; text-align: right; font-weight: 600;">${frappe.utils.escape_html(
										w.actual
									)}</td>
									<td style="padding: 8px 10px; text-align: right; color: var(--text-muted, #64748b);">${frappe.utils.escape_html(
										w.standard
									)}</td>
									<td style="padding: 8px 10px; text-align: right; font-weight: 700; color: ${
										w.type === "danger" ? "#dc2626" : "#d97706"
									};">${frappe.utils.escape_html(w.variance)}</td>
									<td style="padding: 8px 10px;">
										<span style="display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; background-color: ${
											w.type === "danger" ? "#fee2e2" : "#fef3c7"
										}; color: ${
										w.type === "danger" ? "#991b1b" : "#92400e"
									}; border: 1px solid ${
										w.type === "danger" ? "#fca5a5" : "#fde68a"
									};">
											${frappe.utils.escape_html(w.issue)}
										</span>
									</td>
								</tr>
							`
								)
								.join("")}
						</tbody>
					</table>
				</div>
			</div>
			`;
		} else {
			modal_content = `
			<div class="text-center p-4 my-2" style="background-color: var(--subtle-accent-background, #f0fdf4); border: 1px solid #bbf7d0; border-radius: 6px;">
				<div style="font-size: 28px; color: #16a34a; line-height: 1; margin-bottom: 8px;">✓</div>
				<div style="font-weight: 700; color: #15803d; font-size: 14px;">${__(
					"All Batches Meet Standard Benchmarks"
				)}</div>
				<div class="text-muted small mt-1 mb-0">${__(
					"No abnormal variances detected in body weight, egg production (HDEP), mortality, or feed intake."
				)}</div>
			</div>
			`;
		}

		d.fields_dict.modal_html.$wrapper.html(modal_content);
		d.show();
	},

	check_benchmark_deviations_alert(frm) {
		// Handled via modal dialog
	},

	filter_tables_by_shed(frm, current_shed) {
		if (!current_shed) current_shed = frm.doc.selected_shed;
		if (!current_shed) return;

		["egg_entries", "feed_entries", "flock_entries", "sales_entries"].forEach(function (
			fieldname
		) {
			let field = frm.fields_dict[fieldname];
			if (!field || !field.grid) return;

			let grid = field.grid;
			let do_filter = function () {
				if (!grid.grid_rows) return;
				grid.grid_rows.forEach(function (row) {
					if (row && row.wrapper) {
						if (row.doc.shed && row.doc.shed !== current_shed) {
							row.wrapper.hide();
						} else {
							row.wrapper.show();
						}
					}
				});
				frm.events.render_table_totals(frm, fieldname);
			};

			do_filter();
			grid.wrapper
				.off("grid-row-render.pdl_filter")
				.on("grid-row-render.pdl_filter", function () {
					do_filter();
				});
		});
	},

	render_all_table_totals(frm) {
		["shed_entries", "egg_entries", "feed_entries", "flock_entries", "sales_entries"].forEach(
			function (fn) {
				frm.events.render_table_totals(frm, fn);
			}
		);
	},

	render_table_totals(frm, fieldname) {
		let field = frm.fields_dict[fieldname];
		if (!field || !field.grid || !field.grid.wrapper) return;

		let grid = field.grid;
		let $head_row = grid.wrapper.find(".grid-heading-row .data-row");
		if (!$head_row.length) return;

		let is_shed_list = fieldname === "shed_entries";
		let current_shed = frm.doc.selected_shed;
		let visible_rows = (frm.doc[fieldname] || []).filter(function (r) {
			if (is_shed_list) return true;
			return !current_shed || r.shed === current_shed;
		});

		let $grid_body = grid.wrapper.find(".grid-body");
		if (!$grid_body.length) return;

		let $totals_row = $grid_body.find(".grid-totals-row");
		if (!$totals_row.length) {
			$totals_row = $(`
				<div class="grid-row grid-totals-row">
					<div class="data-row row m-0"></div>
				</div>
			`);
			$grid_body.append($totals_row);
		}

		if (!visible_rows.length) {
			$totals_row.hide();
			return;
		} else {
			$totals_row.show();
		}

		let $container = $totals_row.find(".data-row");
		$container.empty();

		// Calculate total opening birds for production % if needed
		let total_opening_birds = 0;
		(frm.doc.flock_entries || []).forEach((f) => {
			if (!current_shed || f.shed === current_shed)
				total_opening_birds += flt(f.opening_birds) || 0;
		});

		let total_eggs_all = 0;
		let total_broken_all = 0;
		if (fieldname === "egg_entries") {
			visible_rows.forEach((r) => {
				total_eggs_all += flt(r.total_eggs) || 0;
				total_broken_all += flt(r.broken_eggs) || 0;
			});
		}

		let first_data_col_handled = false;

		// Loop through each header column to create an identical, aligned totals cell
		$head_row.children().each(function () {
			let $th = $(this);
			let fn = $th.attr("data-fieldname");
			let col_class = $th.attr("class") || "col grid-static-col";
			let col_style = $th.attr("style") || "";

			let $td = $(`<div class="${col_class}" style="${col_style}"></div>`);
			$td.attr("data-fieldname", fn || "");

			// 1. Checkbox column: keep empty
			if ($th.hasClass("row-check") || $th.find(".grid-row-check").length) {
				$td.html("");
				$td.css({ padding: "8px 4px", "min-width": $th.css("width") || "auto" });
			}
			// 2. Row index ("No.") column: keep empty
			else if ($th.hasClass("row-index")) {
				$td.html("");
				$td.css({ padding: "8px 4px", "min-width": $th.css("width") || "auto" });
			}
			// 3. First data column (e.g. Batch or Shed Name): display "TOTAL" label here cleanly aligned
			else if (!first_data_col_handled && fn) {
				first_data_col_handled = true;
				$td.html(
					'<span style="font-weight: 700; color: var(--text-color, #0f172a); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Total</span>'
				);
				$td.css({
					padding: "8px 10px",
					"text-align": "left",
					display: "flex",
					"align-items": "center",
				});
			}
			// 4. Data columns with numeric calculations
			else if (fn) {
				let meta_field = frappe.meta.get_docfield(grid.df.options, fn);
				let ft = meta_field ? meta_field.fieldtype : "";

				let sum = 0;
				let has_numeric = false;
				visible_rows.forEach(function (r) {
					if (r[fn] !== undefined && r[fn] !== null && r[fn] !== "") {
						has_numeric = true;
						sum += flt(r[fn]);
					}
				});

				let cell_html = "";
				let align_right = false;

				if (fn === "tray_summary") {
					let trays = Math.floor(total_eggs_all / 30);
					let left = total_eggs_all % 30;
					cell_html = `<span style="font-weight: 700; color: var(--text-color, #0f172a); font-size: 11px;">${trays} Trays, ${left} Eggs</span>`;
				} else if (fn === "egg_production_pct") {
					let pct =
						total_opening_birds > 0
							? ((total_eggs_all / total_opening_birds) * 100).toFixed(1)
							: "0.0";
					cell_html = `<span style="font-weight: 700; color: var(--text-color, #0f172a); font-size: 11px;">${pct}%</span>`;
					align_right = true;
				} else if (fn === "broken_egg_pct") {
					let pct =
						total_eggs_all > 0
							? ((total_broken_all / total_eggs_all) * 100).toFixed(1)
							: "0.0";
					cell_html = `<span style="font-weight: 700; color: var(--text-color, #0f172a); font-size: 11px;">${pct}%</span>`;
					align_right = true;
				} else if (fn === "feed_spent_g_per_bird") {
					let total_feed_kg = 0;
					visible_rows.forEach((r) => (total_feed_kg += flt(r.feed_spent_kg) || 0));
					let g_bird =
						total_opening_birds > 0
							? ((total_feed_kg * 1000) / total_opening_birds).toFixed(1)
							: "0.0";
					cell_html = `<span style="font-weight: 700; color: var(--text-color, #0f172a); font-size: 11px;">${g_bird}</span>`;
					align_right = true;
				} else if (fn === "average_body_weight_g") {
					let total_wt = 0;
					let count = 0;
					visible_rows.forEach((r) => {
						if (flt(r.average_body_weight_g) > 0) {
							total_wt += flt(r.average_body_weight_g);
							count += 1;
						}
					});
					let avg_str = count > 0 ? (total_wt / count).toFixed(1) + " g" : "—";
					cell_html = `<span style="font-weight: 700; color: var(--text-color, #0f172a); font-size: 11px;">${avg_str}</span>`;
					align_right = true;
				} else if (
					["Int", "Check"].includes(ft) ||
					[
						"batches_count",
						"total_birds",
						"in_stock",
						"good_eggs",
						"double_yolk_eggs",
						"broken_eggs",
						"waste_eggs",
						"total_eggs",
						"opening_birds",
						"dead",
						"culled",
						"closing_birds",
					].includes(fn)
				) {
					cell_html = `<span style="font-weight: 700; color: var(--text-color, #0f172a); font-size: 12px;">${Math.round(
						sum
					).toLocaleString()}</span>`;
					align_right = true;
				} else if (
					["Float", "Currency"].includes(ft) &&
					![
						"rate",
						"rate_per_kg",
						"table_egg_rate",
						"broken_egg_rate",
						"average_body_weight_g",
					].includes(fn)
				) {
					let formatted = ft === "Currency" ? format_currency(sum) : sum.toFixed(2);
					cell_html = `<span style="font-weight: 700; color: var(--text-color, #0f172a); font-size: 12px;">${formatted}</span>`;
					align_right = true;
				}

				$td.html(cell_html);
				if (align_right) {
					$td.css({
						"text-align": "right",
						"justify-content": "flex-end",
						padding: "8px 10px",
					});
				} else {
					$td.css({ padding: "8px 10px" });
				}
			} else {
				$td.html("");
			}

			$container.append($td);
		});
	},

	log_date(frm) {
		if (frm.doc.log_date) {
			let dt = moment(frm.doc.log_date);
			frm.set_value("day_of_week", dt.format("dddd"));
			if (frm.doc.selected_shed) {
				frm.trigger("load_shed_context");
			}
		}
	},

	validate(frm) {
		if (frm.__saving_with_benchmark_approved) {
			frm.__saving_with_benchmark_approved = false;
			return;
		}

		if (frm.doc.docstatus === 1) {
			return;
		}

		let shed =
			frm.doc.selected_shed ||
			(frm.doc.shed_entries && frm.doc.shed_entries.length
				? frm.doc.shed_entries[0].shed
				: null);
		if (!shed) {
			return;
		}

		// Halt standard synchronous save to display benchmark comparison popup
		frappe.validated = false;

		let check_and_show = function () {
			let ctx = frm.__current_shed_context || {};
			let batches = ctx.batches || [];
			let has_benchmarks = batches.some((b) => {
				let bmk = b.benchmark || {};
				return (
					flt(bmk.standard_body_weight_g) > 0 ||
					flt(bmk.standard_hdep_pct) > 0 ||
					flt(bmk.standard_mortality_pct) > 0
				);
			});

			if (!has_benchmarks) {
				// No standard benchmarks found; proceed with saving
				frm.__saving_with_benchmark_approved = true;
				frm.save().finally(() => {
					frm.__saving_with_benchmark_approved = false;
				});
				return;
			}

			frm.events.show_benchmark_comparison_dialog(frm, function () {
				frm.__saving_with_benchmark_approved = true;
				frm.save().finally(() => {
					frm.__saving_with_benchmark_approved = false;
				});
			});
		};

		if (!frm.__current_shed_context && shed) {
			frappe.call({
				method: "ob_poultry.poultry.doctype.poultry_daily_log.poultry_daily_log.get_shed_context",
				args: {
					log_date: frm.doc.log_date || frappe.datetime.nowdate(),
					shed: shed,
				},
				callback: function (r) {
					frm.__current_shed_context = r.message || {};
					check_and_show();
				},
				error: function () {
					frm.__saving_with_benchmark_approved = true;
					frm.save().finally(() => {
						frm.__saving_with_benchmark_approved = false;
					});
				},
			});
		} else {
			check_and_show();
		}
	},

	average_body_weight_g(frm) {
		frm.events.render_benchmark_variance_card(frm);
	},

	record_weight(frm) {
		frm.events.toggle_weight_field(frm);
		if (!cint(frm.doc.record_weight)) {
			frm.set_value("average_body_weight_g", 0);
		}
	},

	water_consumption_liters(frm) {
		frm.trigger("calculate_all_totals");
	},

	toggle_weight_field(frm) {
		let checked = cint(frm.doc.record_weight) === 1;
		if (checked) {
			$(frm.wrapper).removeClass("hide-pdl-weight");
		} else {
			$(frm.wrapper).addClass("hide-pdl-weight");
		}
		if (frm.fields_dict.flock_entries && frm.fields_dict.flock_entries.grid) {
			try {
				frm.fields_dict.flock_entries.grid.set_column_disp(
					"average_body_weight_g",
					checked
				);
				frm.fields_dict.flock_entries.grid.refresh();
			} catch (e) {
				// handled by CSS
			}
		}
		frm.events.render_table_totals(frm, "flock_entries");
	},

	calculate_all_totals(frm) {
		if (frm.doc.docstatus === 1) {
			// Submitted documents should not mutate values and show Not Saved
			frm.events.render_all_table_totals(frm);
			return;
		}

		// Calculate Eggs
		let total_eggs = 0;
		let good_eggs = 0;
		(frm.doc.egg_entries || []).forEach((r) => {
			total_eggs += flt(r.total_eggs) || 0;
			good_eggs += (flt(r.good_eggs) || 0) + (flt(r.double_yolk_eggs) || 0);
		});
		frm.set_value("total_eggs_produced", total_eggs);

		// Calculate Feeds
		let total_feed_kg = 0;
		let total_feed_cost = 0;
		(frm.doc.feed_entries || []).forEach((r) => {
			total_feed_kg += flt(r.feed_spent_kg) || 0;
			total_feed_cost += flt(r.total_feed_cost) || 0;
		});
		frm.set_value("total_feed_consumed_kg", total_feed_kg);
		frm.set_value("total_feed_cost", total_feed_cost);

		// Layer KPIs: Feed Cost per Egg
		let feed_cost_per_egg =
			good_eggs > 0 && total_feed_cost > 0
				? flt((total_feed_cost / good_eggs).toFixed(2))
				: 0;
		frm.set_value("feed_cost_per_egg", feed_cost_per_egg);

		// Calculate Flock
		let total_mortality = 0;
		let total_culls = 0;
		let total_closing = 0;
		let total_weight = 0;
		let weight_count = 0;
		(frm.doc.flock_entries || []).forEach((r) => {
			total_mortality += flt(r.dead) || 0;
			total_culls += flt(r.culled) || 0;
			total_closing += flt(r.closing_birds) || 0;
			if (flt(r.average_body_weight_g) > 0) {
				total_weight += flt(r.average_body_weight_g);
				weight_count += 1;
			}
		});
		frm.set_value("total_mortality", total_mortality);
		frm.set_value("total_culled", total_culls);
		if (cint(frm.doc.record_weight) === 1 && weight_count > 0) {
			frm.set_value("average_body_weight_g", flt((total_weight / weight_count).toFixed(2)));
		} else if (!cint(frm.doc.record_weight)) {
			frm.set_value("average_body_weight_g", 0);
		}

		// Environmental / Water calculations
		let water = flt(frm.doc.water_consumption_liters) || 0;
		let water_per_bird =
			total_closing > 0 && water > 0 ? flt(((water * 1000) / total_closing).toFixed(2)) : 0;
		let water_feed_ratio =
			total_feed_kg > 0 && water > 0 ? flt((water / total_feed_kg).toFixed(2)) : 0;
		frm.set_value("water_per_bird_ml", water_per_bird);
		frm.set_value("water_feed_ratio", water_feed_ratio);

		// Calculate Sales
		let total_sales = 0;
		(frm.doc.sales_entries || []).forEach((r) => {
			total_sales += flt(r.total_amount) || 0;
		});
		frm.set_value("total_sales_amount", total_sales);

		// Hen-Housed Production % (HHEP)
		let total_initial = 0;
		(frm.doc.flock_entries || []).forEach((f) => {
			if (frm._batch_initial_counts && frm._batch_initial_counts[f.batch]) {
				total_initial += flt(frm._batch_initial_counts[f.batch]);
			}
		});
		if (total_initial > 0 && total_eggs > 0) {
			frm.set_value(
				"hen_housed_production_pct",
				flt(((total_eggs / total_initial) * 100).toFixed(2))
			);
		} else if (total_closing > 0 && total_eggs > 0 && !frm.doc.hen_housed_production_pct) {
			frm.set_value(
				"hen_housed_production_pct",
				flt(((total_eggs / total_closing) * 100).toFixed(2))
			);
		}

		// Update vertical totals on all tables
		frm.events.render_all_table_totals(frm);
		frm.events.render_benchmark_variance_card(frm);
	},
});

// Intercept child row render to close grid form and open data entry view
frappe.ui.form.on("Poultry Daily Log Shed Entry", {
	form_render(frm, cdt, cdn) {
		frappe.ui.form.close_grid_form();
		$(".form-in-grid, .modal:visible, .modal-backdrop").remove();
		$("body").removeClass("modal-open");
		let row = locals[cdt][cdn];
		if (row && row.shed) {
			frm.events.show_data_entry_view(frm, row.shed, true);
		}
	},
});

// Real-time calculations on Eggs Table
frappe.ui.form.on("Poultry Daily Log Egg Entry", {
	good_eggs(frm, cdt, cdn) {
		calculate_egg_row(frm, cdt, cdn);
	},
	double_yolk_eggs(frm, cdt, cdn) {
		calculate_egg_row(frm, cdt, cdn);
	},
	broken_eggs(frm, cdt, cdn) {
		calculate_egg_row(frm, cdt, cdn);
	},
	waste_eggs(frm, cdt, cdn) {
		calculate_egg_row(frm, cdt, cdn);
	},
	egg_entries_add(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.shed) row.shed = frm.doc.selected_shed;
	},
});

function calculate_egg_row(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let total =
		(flt(row.good_eggs) || 0) +
		(flt(row.double_yolk_eggs) || 0) +
		(flt(row.broken_eggs) || 0) +
		(flt(row.waste_eggs) || 0);
	let broken = flt(row.broken_eggs) || 0;
	let broken_pct = total > 0 ? ((broken / total) * 100).toFixed(2) : 0;
	let trays = Math.floor(total / 30);
	let left = total % 30;

	// Find opening birds from flock entry
	let opening_birds = 0;
	(frm.doc.flock_entries || []).forEach((f) => {
		if (f.batch === row.batch) opening_birds = flt(f.opening_birds) || 0;
	});
	let prod_pct = opening_birds > 0 ? ((total / opening_birds) * 100).toFixed(2) : 0;

	frappe.model.set_value(cdt, cdn, "total_eggs", total);
	frappe.model.set_value(cdt, cdn, "broken_egg_pct", flt(broken_pct));
	frappe.model.set_value(cdt, cdn, "egg_production_pct", flt(prod_pct));
	frappe.model.set_value(cdt, cdn, "trays", trays);
	frappe.model.set_value(cdt, cdn, "eggs_left", left);
	frappe.model.set_value(cdt, cdn, "tray_summary", `${trays} Trays, ${left} Eggs`);

	// Calculate HHEP %
	if (
		row.batch &&
		(!frm._batch_initial_counts || frm._batch_initial_counts[row.batch] === undefined)
	) {
		if (!frm._batch_initial_counts) frm._batch_initial_counts = {};
		frappe.db.get_value("Poultry Batch", row.batch, "initial_bird_count").then((r) => {
			let init_count =
				(r && r.message && r.message.initial_bird_count) || opening_birds || 0;
			frm._batch_initial_counts[row.batch] = init_count;
			let hhep = init_count > 0 ? ((total / init_count) * 100).toFixed(2) : 0;
			frappe.model.set_value(cdt, cdn, "hhep_pct", flt(hhep));
			frm.trigger("calculate_all_totals");
		});
	} else {
		let init_count =
			(frm._batch_initial_counts && frm._batch_initial_counts[row.batch]) ||
			opening_birds ||
			0;
		let hhep = init_count > 0 ? ((total / init_count) * 100).toFixed(2) : 0;
		frappe.model.set_value(cdt, cdn, "hhep_pct", flt(hhep));
		frm.trigger("calculate_all_totals");
	}
}

// Real-time calculations on Feeds Table
frappe.ui.form.on("Poultry Daily Log Feed Entry", {
	feed_spent_kg(frm, cdt, cdn) {
		calculate_feed_row(frm, cdt, cdn);
	},
	rate_per_kg(frm, cdt, cdn) {
		calculate_feed_row(frm, cdt, cdn);
	},
	warehouse(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.warehouse) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Bin",
					filters: { warehouse: row.warehouse, item_code: row.feed_item || "" },
					fieldname: ["actual_qty", "valuation_rate"],
				},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(
							cdt,
							cdn,
							"opening_stock_kg",
							flt(r.message.actual_qty) || 0
						);
						if (flt(r.message.valuation_rate)) {
							frappe.model.set_value(
								cdt,
								cdn,
								"rate_per_kg",
								flt(r.message.valuation_rate)
							);
						}
						calculate_feed_row(frm, cdt, cdn);
					}
				},
			});
		}
	},
	feed_entries_add(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.shed) row.shed = frm.doc.selected_shed;
	},
});

function calculate_feed_row(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let spent = flt(row.feed_spent_kg) || 0;
	let opening = flt(row.opening_stock_kg) || 0;
	let rate = flt(row.rate_per_kg) || 0;

	let opening_birds = 0;
	(frm.doc.flock_entries || []).forEach((f) => {
		if (f.batch === row.batch) opening_birds = flt(f.opening_birds) || 0;
	});

	let g_per_bird = opening_birds > 0 ? ((spent * 1000) / opening_birds).toFixed(2) : 0;
	let available = Math.max(0, opening - spent);
	let cost = spent * rate;

	frappe.model.set_value(cdt, cdn, "feed_spent_g_per_bird", flt(g_per_bird));
	frappe.model.set_value(cdt, cdn, "currently_available_kg", flt(available));
	frappe.model.set_value(cdt, cdn, "total_feed_cost", flt(cost));

	frm.trigger("calculate_all_totals");
}

// Real-time calculations on Chickens Table
frappe.ui.form.on("Poultry Daily Log Flock Entry", {
	dead(frm, cdt, cdn) {
		calculate_flock_row(frm, cdt, cdn);
	},
	culled(frm, cdt, cdn) {
		calculate_flock_row(frm, cdt, cdn);
	},
	average_body_weight_g(frm) {
		let total_wt = 0;
		let count = 0;
		(frm.doc.flock_entries || []).forEach((row) => {
			if (flt(row.average_body_weight_g) > 0) {
				total_wt += flt(row.average_body_weight_g);
				count += 1;
			}
		});
		let avg = count > 0 ? flt((total_wt / count).toFixed(2)) : 0;
		frm.set_value("average_body_weight_g", avg);
		frm.events.render_table_totals(frm, "flock_entries");
	},
	flock_entries_add(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.shed) row.shed = frm.doc.selected_shed;
	},
});

function calculate_flock_row(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let opening = flt(row.opening_birds) || 0;
	let dead = flt(row.dead) || 0;
	let culled = flt(row.culled) || 0;
	let closing = Math.max(0, opening - dead - culled);

	frappe.model.set_value(cdt, cdn, "closing_birds", closing);
	frm.trigger("calculate_all_totals");

	// Update Egg and Feed calculations if birds changed
	(frm.doc.egg_entries || []).forEach((e) => {
		if (e.batch === row.batch && e.name) {
			calculate_egg_row(frm, e.doctype, e.name);
		}
	});
	(frm.doc.feed_entries || []).forEach((fe) => {
		if (fe.batch === row.batch && fe.name) {
			calculate_feed_row(frm, fe.doctype, fe.name);
		}
	});
}

// Real-time calculations on Sales Table
frappe.ui.form.on("Poultry Daily Log Sales Entry", {
	good_eggs(frm, cdt, cdn) {
		calculate_sales_row(frm, cdt, cdn);
	},
	double_yolk_eggs(frm, cdt, cdn) {
		calculate_sales_row(frm, cdt, cdn);
	},
	broken_eggs(frm, cdt, cdn) {
		calculate_sales_row(frm, cdt, cdn);
	},
	table_egg_rate(frm, cdt, cdn) {
		calculate_sales_row(frm, cdt, cdn);
	},
	broken_egg_rate(frm, cdt, cdn) {
		calculate_sales_row(frm, cdt, cdn);
	},
	rate(frm, cdt, cdn) {
		calculate_sales_row(frm, cdt, cdn);
	},
	sales_entries_add(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.shed) row.shed = frm.doc.selected_shed;
	},
});

function calculate_sales_row(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let table_rate = flt(row.table_egg_rate) || flt(row.rate) || 0;
	let broken_rate = flt(row.broken_egg_rate) || 0;
	let table_eggs = cint(row.good_eggs) || 0;
	let broken_eggs = cint(row.broken_eggs) || 0;

	let table_amount = Math.round(table_eggs * table_rate * 100) / 100;
	let broken_amount = Math.round(broken_eggs * broken_rate * 100) / 100;
	let total_amount = Math.round((table_amount + broken_amount) * 100) / 100;

	frappe.model.set_value(cdt, cdn, "table_egg_rate", table_rate);
	frappe.model.set_value(cdt, cdn, "table_egg_amount", table_amount);
	frappe.model.set_value(cdt, cdn, "broken_egg_rate", broken_rate);
	frappe.model.set_value(cdt, cdn, "broken_egg_amount", broken_amount);
	frappe.model.set_value(cdt, cdn, "total_amount", total_amount);
	frm.trigger("calculate_all_totals");
}

// Prevent modal dialog popup on all child doctypes: allow in-place cell editing only
[
	"Poultry Daily Log Egg Entry",
	"Poultry Daily Log Feed Entry",
	"Poultry Daily Log Flock Entry",
	"Poultry Daily Log Sales Entry",
].forEach(function (dt) {
	frappe.ui.form.on(dt, {
		form_render(frm) {
			cur_dialog && cur_dialog.hide && cur_dialog.hide();
			frappe.ui.form.close_grid_form();
			$(".modal:visible, .modal-backdrop").remove();
			$("body").removeClass("modal-open");
		},
	});
});
