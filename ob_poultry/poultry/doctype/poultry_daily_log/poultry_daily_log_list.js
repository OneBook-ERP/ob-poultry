frappe.listview_settings["Poultry Daily Log"] = {
	hide_name_column: false,
	has_indicator_for_draft: false,
	has_indicator_for_cancelled: false,
	get_indicator: function () {
		return false;
	},

	onload: function (listview) {
		frappe.dom.set_style(`
			[data-page-route="List/Poultry Daily Log/List"] [data-fieldname="status_field"],
			[data-page-route="List/Poultry Daily Log/List"] .list-item__content--indicator,
			[data-page-route="List/Poultry Daily Log/List"] .indicator-pill {
				display: none !important;
			}
		`);

		// Replace default "Add Poultry Daily Log" with "Add today's log"
		let today = frappe.datetime.get_today();

		// Check if a log has already been created for today
		frappe.db.get_value("Poultry Daily Log", { log_date: today }, ["name"], (r) => {
			if (r && r.name) {
				// Record already created for today -> Lock the button!
				listview.page.set_primary_action(__("Add today's log"), null, "lock");
				if (listview.page.primary_action) {
					listview.page.primary_action
						.prop("disabled", true)
						.addClass("btn-secondary disabled")
						.removeClass("btn-primary")
						.attr(
							"title",
							__(
								"Today's log has already been created (Record: " +
									r.name +
									"). Click on today's row to view or edit."
							)
						);
				}
			} else {
				// No record yet for today -> Button active
				listview.page.set_primary_action(
					__("Add today's log"),
					() => {
						frappe.new_doc("Poultry Daily Log", {
							log_date: today,
						});
					},
					"add"
				);
			}
		});
	},

	refresh: function (listview) {
		// Only hide status column/pills, keep all table column headers (ID, Log Date, Day) intact
		listview.page.wrapper.find('[data-fieldname="status_field"]').hide();
		listview.$result
			.find(
				'.level-item:has(.indicator-pill), [data-fieldname="status_field"], .list-item__content--indicator'
			)
			.hide();

		// Highlight today's row in the list view for easy discovery
		let today = frappe.datetime.get_today();
		listview.$result.find(".list-row").each(function () {
			let date_text = $(this).find('.list-row-col:contains("' + today + '")');
			if (date_text.length) {
				$(this).css("border-left", "4px solid var(--primary)");
			}
		});
	},
};
