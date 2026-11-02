import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, date_diff, flt, nowdate


class PoultryBatch(Document):
	def onload(self):
		self.load_daily_logs_history()

	def validate(self):
		if not self.is_new():
			db_doc = self.get_doc_before_save()
			if db_doc:
				if self.breed != db_doc.breed:
					frappe.throw(_("Breed cannot be changed once the batch is created."))
				if cint(self.initial_bird_count) != cint(db_doc.initial_bird_count):
					frappe.throw(_("Initial Bird Count cannot be changed once the batch is created."))

		if not self.initial_shed and self.shed:
			self.initial_shed = self.shed
		self.update_batch_week()
		self.validate_layer_sexed_counts()
		self.validate_shed_capacity()
		self.default_feed_warehouse_from_shed()
		self.validate_contract_fields()
		if self.is_new():
			self.current_bird_count = self.initial_bird_count
		if self.get("shed_transfers"):
			self.update_transfer_remaining_birds()

	def update_batch_week(self):
		if not self.start_date:
			self.batch_week = 0
			return
		ref_date = self.end_date if (self.status == "Closed" and self.end_date) else nowdate()
		days = date_diff(ref_date, self.start_date)
		self.batch_week = max(0, int(flt(days) // 7))

	def validate_layer_sexed_counts(self):
		if self.breed_type == "Layer":
			self.male_bird_count = 0
			if self.initial_bird_count:
				self.female_bird_count = self.initial_bird_count
			elif self.female_bird_count:
				self.initial_bird_count = self.female_bird_count

	def get_initial_shed(self):
		if self.initial_shed:
			return self.initial_shed
		if self.get("shed_transfers"):
			return self.shed_transfers[0].from_shed
		return self.shed

	def get_shed_bird_counts(self):
		"""
		Returns a dict {shed_name: bird_count} of current bird distribution across sheds.
		"""
		counts = {}
		init_shed = self.get_initial_shed()
		if init_shed:
			counts[init_shed] = int(flt(self.initial_bird_count or 0))

		for t in self.get("shed_transfers", []):
			from_s = t.from_shed
			to_s = t.to_shed
			qty_out = int(flt(t.birds_to_transfer or t.birds_moved or 0))
			transit = int(flt(t.transit_mortality or 0))
			qty_in = int(flt(t.birds_moved or (qty_out - transit)))

			counts[from_s] = counts.get(from_s, 0) - qty_out
			counts[to_s] = counts.get(to_s, 0) + qty_in

		return {shed: max(0, count) for shed, count in counts.items()}

	def get_source_shed_remaining(self, from_shed=None):
		if not from_shed:
			from_shed = self.shed
		counts = self.get_shed_bird_counts()
		return counts.get(from_shed, 0)

	def update_transfer_remaining_birds(self):
		counts = self.get_shed_bird_counts()
		for row in self.get("shed_transfers", []):
			rem = counts.get(row.from_shed, 0)
			row.remaining_birds = rem
			if getattr(row, "name", None) and not str(row.name).startswith("new-"):
				frappe.db.set_value(
					"Poultry Batch Shed Transfer",
					row.name,
					"remaining_birds",
					rem,
					update_modified=False,
				)

	def validate_shed_capacity(self):
		capacity = frappe.db.get_value("Poultry Shed", self.shed, "capacity")
		birds_to_check = (
			self.current_bird_count
			if (not self.is_new() and self.get("shed_transfers"))
			else self.initial_bird_count
		)
		if capacity and birds_to_check > capacity:
			frappe.throw(
				_("Bird Count ({0}) exceeds the capacity ({1}) of Shed {2}").format(
					birds_to_check, capacity, self.shed
				)
			)

	def default_feed_warehouse_from_shed(self):
		if not self.is_new() or self.feed_warehouse or not self.shed:
			return
		default_warehouse = frappe.db.get_value("Poultry Shed", self.shed, "default_feed_warehouse")
		if default_warehouse:
			self.feed_warehouse = default_warehouse

	def validate_contract_fields(self):
		if self.flock_source != "Contract":
			return
		if not self.farmer:
			frappe.throw(_("Set a Farmer for a Contract flock"))
		if not self.growing_charge_scheme:
			frappe.throw(_("Set a Growing Charge Scheme for a Contract flock"))

	def after_insert(self):
		self.create_vaccination_due_rows()

	def create_vaccination_due_rows(self):
		template_name = frappe.db.get_value(
			"Poultry Vaccination Schedule Template", {"breed": self.breed, "is_active": 1}
		)
		if not template_name:
			return
		template = frappe.get_doc("Poultry Vaccination Schedule Template", template_name)
		for row in template.get_due_rows(self.name, self.start_date):
			frappe.get_doc({"doctype": "Poultry Vaccination Due", **row}).insert(ignore_permissions=True)

	@frappe.whitelist()
	def close_batch(self):
		if self.status == "Closed":
			frappe.throw(_("Batch {0} is already closed").format(self.name))
		self.status = "Closed"
		self.end_date = self.end_date or nowdate()
		self.save()

	@frappe.whitelist()
	def calculate_growing_charge(self):
		if self.flock_source != "Contract" or not self.growing_charge_scheme:
			frappe.throw(_("Set Flock Source to Contract and choose a Growing Charge Scheme first"))
		latest_weight_g = frappe.db.get_value(
			"Poultry Daily Log",
			{"batch": self.name, "docstatus": 1, "average_body_weight_g": [">", 0]},
			"average_body_weight_g",
			order_by="log_date desc",
		)
		if not latest_weight_g:
			frappe.throw(_("No body weight has been recorded for batch {0} yet").format(self.name))
		scheme = frappe.get_doc("Poultry Growing Charge Scheme", self.growing_charge_scheme)
		rate_per_kg = scheme.get_rate_for_weight(latest_weight_g)
		total_weight_kg = flt(self.current_bird_count) * flt(latest_weight_g) / 1000
		amount = total_weight_kg * flt(rate_per_kg)
		self.db_set("growing_charge_amount", amount)
		return amount

	@frappe.whitelist()
	def get_shed_summary(self):
		return {
			"initial_shed": self.get_initial_shed(),
			"current_shed": self.shed,
			"shed_counts": self.get_shed_bird_counts(),
		}

	@frappe.whitelist()
	def load_daily_logs_history(self):
		if not self.name or self.is_new():
			return []
		logs = get_batch_daily_logs_and_sales(self.name)
		self.set("daily_logs", [])
		for log in logs:
			sales_rows = ""
			for s in log.get("sales", []):
				customer = frappe.utils.escape_html(s.get("customer") or _("Walk-in Customer"))
				good_eggs = cint(s.get("good_eggs"))
				table_egg_rate = flt(s.get("table_egg_rate"))
				broken_eggs = cint(s.get("broken_eggs"))
				broken_egg_rate = flt(s.get("broken_egg_rate"))
				total_amt = frappe.format_value(s.get("total_amount"), {"fieldtype": "Currency"})
				sales_rows += f"""<tr style="border-bottom: 1px solid var(--border-color);">
					<td style="padding: 6px 10px;">{customer}</td>
					<td style="padding: 6px 10px; text-align: right;">{good_eggs:,} @ ₹{table_egg_rate:.2f}</td>
					<td style="padding: 6px 10px; text-align: right;">{broken_eggs:,} @ ₹{broken_egg_rate:.2f}</td>
					<td style="padding: 6px 10px; text-align: right; font-weight: 600; color: var(--green-600, #057a55);">{total_amt}</td>
				</tr>"""

			if sales_rows:
				total_sales_display = frappe.format_value(
					log.get("total_sales_amount"), {"fieldtype": "Currency"}
				)
				sales_html = f"""<table class="table table-bordered table-sm" style="width: 100%; margin-top: 6px; font-size: 12px; background: var(--card-bg, #fff);">
					<thead>
						<tr style="background-color: var(--table-header-bg, #f4f5f6); color: var(--text-muted);">
							<th style="padding: 6px 10px;">{_("Customer")}</th>
							<th style="padding: 6px 10px; text-align: right;">{_("Table Eggs")}</th>
							<th style="padding: 6px 10px; text-align: right;">{_("Broken Eggs")}</th>
							<th style="padding: 6px 10px; text-align: right;">{_("Total Amount")}</th>
						</tr>
					</thead>
					<tbody>{sales_rows}</tbody>
					<tfoot>
						<tr style="font-weight: 600; background: var(--table-header-bg, #f4f5f6);">
							<td colspan="3" style="padding: 6px 10px; text-align: right;">{_("Total Sales Amount:")}</td>
							<td style="padding: 6px 10px; text-align: right; color: var(--green-600, #057a55);">{total_sales_display}</td>
						</tr>
					</tfoot>
				</table>"""
			else:
				sales_html = f'<div class="text-muted" style="padding: 10px 0; font-size: 12px; font-style: italic;">{_("No egg sales recorded on this daily log for this batch.")}</div>'

			self.append(
				"daily_logs",
				{
					"doctype": "Poultry Batch Daily Log Entry",
					"daily_log": log.get("log_name"),
					"log_date": log.get("log_date"),
					"shed": log.get("shed"),
					"week_day": log.get("week_day"),
					"mortality": log.get("mortality"),
					"feed_consumed_kg": log.get("feed_consumed_kg"),
					"total_eggs": log.get("total_eggs"),
					"total_sales_amount": log.get("total_sales_amount"),
					"day_of_week": log.get("day_of_week"),
					"opening_birds": log.get("opening_birds"),
					"culled": log.get("culled"),
					"closing_birds": log.get("closing_birds"),
					"feed_item": log.get("feed_item"),
					"feed_cost": log.get("feed_cost"),
					"good_eggs": log.get("good_eggs"),
					"broken_eggs": log.get("broken_eggs"),
					"double_yolk_eggs": log.get("double_yolk_eggs"),
					"egg_production_pct": log.get("egg_production_pct"),
					"tray_summary": log.get("tray_summary"),
					"sales_details_html": sales_html,
				},
			)
		return self.daily_logs

	@frappe.whitelist()
	def transfer_shed(
		self,
		new_shed,
		from_shed=None,
		transfer_date=None,
		birds_to_transfer=None,
		transit_mortality=0,
		notes=None,
	):
		if self.status == "Closed":
			frappe.throw(_("Batch {0} is closed and cannot be transferred").format(self.name))

		if not new_shed:
			frappe.throw(_("Please select a target shed"))

		from_shed = from_shed or self.shed
		if new_shed == from_shed:
			frappe.throw(_("Target shed must be different from source shed ({0})").format(from_shed))

		shed_doc = frappe.get_doc("Poultry Shed", new_shed)
		if not shed_doc.is_active:
			frappe.throw(_("Target shed {0} is inactive").format(new_shed))

		available_birds = self.get_source_shed_remaining(from_shed)
		if available_birds <= 0:
			frappe.throw(_("No birds remaining in shed {0} to transfer").format(from_shed))

		if birds_to_transfer is None or birds_to_transfer == "":
			birds_to_transfer = available_birds
		birds_to_transfer = int(flt(birds_to_transfer))

		if birds_to_transfer <= 0:
			frappe.throw(_("Number of birds to transfer must be greater than 0"))

		if birds_to_transfer > available_birds:
			frappe.throw(
				_(
					"Number of birds to transfer ({0}) cannot be greater than remaining birds in {1} ({2})"
				).format(birds_to_transfer, from_shed, available_birds)
			)

		transit_mortality = int(flt(transit_mortality or 0))
		if transit_mortality < 0:
			frappe.throw(_("Transit mortality cannot be negative"))

		if transit_mortality > birds_to_transfer:
			frappe.throw(
				_("Transit mortality ({0}) cannot exceed birds to transfer ({1})").format(
					transit_mortality, birds_to_transfer
				)
			)

		transfer_date = transfer_date or nowdate()
		if str(transfer_date) < str(self.start_date):
			frappe.throw(
				_("Transfer date ({0}) cannot be before batch start date ({1})").format(
					transfer_date, self.start_date
				)
			)

		birds_placed = int(birds_to_transfer - transit_mortality)

		if shed_doc.capacity and birds_placed > shed_doc.capacity:
			frappe.throw(
				_("Birds to place ({0}) exceeds capacity ({1}) of new shed {2}").format(
					birds_placed, shed_doc.capacity, new_shed
				)
			)

		self.append(
			"shed_transfers",
			{
				"from_shed": from_shed,
				"to_shed": new_shed,
				"transfer_date": transfer_date,
				"birds_to_transfer": birds_to_transfer,
				"transit_mortality": transit_mortality,
				"birds_moved": birds_placed,
				"reduction": transit_mortality,
				"remaining_birds": available_birds - birds_to_transfer,
				"transferred_by": frappe.session.user,
				"notes": notes or "",
			},
		)

		self.update_transfer_remaining_birds()

		self.shed = new_shed
		if shed_doc.default_feed_warehouse:
			self.feed_warehouse = shed_doc.default_feed_warehouse

		shed_counts = self.get_shed_bird_counts()
		self.current_bird_count = sum(shed_counts.values())
		self.total_mortality = (self.total_mortality or 0) + transit_mortality
		self.save()
		self.recalculate_performance()
		remaining_in_source = shed_counts.get(from_shed, 0)
		frappe.msgprint(
			_(
				"Successfully transferred {0} birds from {1} to {2} ({3} birds placed, {4} transit mortality, {5} remaining in {1})"
			).format(
				birds_to_transfer,
				from_shed,
				new_shed,
				birds_placed,
				transit_mortality,
				remaining_in_source,
			)
		)

	@frappe.whitelist()
	def transfer_to_layer_house(
		self,
		new_shed,
		from_shed=None,
		transfer_date=None,
		transit_mortality=0,
		notes=None,
		birds_to_transfer=None,
	):
		return self.transfer_shed(
			new_shed=new_shed,
			from_shed=from_shed,
			transfer_date=transfer_date,
			birds_to_transfer=birds_to_transfer,
			transit_mortality=transit_mortality,
			notes=notes,
		)

	def recalculate_performance(self):
		totals = frappe.db.sql(
			"""
			select
				sum(mortality_count) as mortality,
				sum(cull_count) as cull,
				sum(feed_consumed_kg) as feed_kg
			from `tabPoultry Daily Log`
			where batch = %s and docstatus = 1
			""",
			self.name,
			as_dict=True,
		)[0]
		transfer_reduction = (
			frappe.db.sql(
				"""
			select sum(reduction)
			from `tabPoultry Batch Shed Transfer`
			where parent = %s
			""",
				self.name,
			)[0][0]
			or 0
		)
		transfer_mortality = (
			frappe.db.sql(
				"""
			select sum(transit_mortality)
			from `tabPoultry Batch Shed Transfer`
			where parent = %s
			""",
				self.name,
			)[0][0]
			or 0
		)
		mortality = (totals.mortality or 0) + transfer_mortality
		removed = (totals.mortality or 0) + (totals.cull or 0) + transfer_reduction
		current_bird_count = self.initial_bird_count - removed
		cumulative_feed_kg = totals.feed_kg or 0

		latest_weight_g = frappe.db.get_value(
			"Poultry Daily Log",
			{"batch": self.name, "docstatus": 1, "average_body_weight_g": [">", 0]},
			"average_body_weight_g",
			order_by="log_date desc",
		)
		fcr = 0
		cfcr = 0
		if latest_weight_g and current_bird_count > 0:
			live_weight_kg = current_bird_count * flt(latest_weight_g) / 1000
			mortality_weight_kg = mortality * flt(latest_weight_g) / 1000
			if live_weight_kg:
				fcr = cumulative_feed_kg / live_weight_kg
			if live_weight_kg + mortality_weight_kg:
				cfcr = cumulative_feed_kg / (live_weight_kg + mortality_weight_kg)

		frappe.db.set_value(
			self.doctype,
			self.name,
			{
				"total_mortality": mortality,
				"current_bird_count": current_bird_count,
				"cumulative_feed_kg": cumulative_feed_kg,
				"fcr": fcr,
				"cfcr": cfcr,
			},
			update_modified=False,
		)


@frappe.whitelist()
def get_batch_daily_logs_and_sales(batch_name: str) -> list[dict]:
	"""Returns all daily log records, flock metrics, feed, egg production, and sales for this batch."""
	if not batch_name:
		return []

	flock_rows = frappe.get_all(
		"Poultry Daily Log Flock Entry",
		filters={"batch": batch_name},
		fields=["parent", "shed", "week_day", "opening_birds", "dead", "culled", "closing_birds"],
	)
	feed_rows = frappe.get_all(
		"Poultry Daily Log Feed Entry",
		filters={"batch": batch_name},
		fields=["parent", "shed", "feed_item", "feed_spent_kg", "feed_spent_g_per_bird", "total_feed_cost"],
	)
	egg_rows = frappe.get_all(
		"Poultry Daily Log Egg Entry",
		filters={"batch": batch_name},
		fields=[
			"parent",
			"shed",
			"in_stock",
			"good_eggs",
			"double_yolk_eggs",
			"broken_eggs",
			"waste_eggs",
			"total_eggs",
			"egg_production_pct",
			"tray_summary",
		],
	)
	sales_rows = frappe.get_all(
		"Poultry Daily Log Sales Entry",
		filters={"batch": batch_name},
		fields=[
			"parent",
			"shed",
			"customer",
			"good_eggs",
			"table_egg_rate",
			"table_egg_amount",
			"broken_eggs",
			"broken_egg_rate",
			"broken_egg_amount",
			"double_yolk_eggs",
			"rate",
			"total_amount",
		],
	)

	parent_names = list(
		{r.parent for r in flock_rows}
		| {r.parent for r in feed_rows}
		| {r.parent for r in egg_rows}
		| {r.parent for r in sales_rows}
	)
	if not parent_names:
		return []

	pdl_docs = frappe.get_all(
		"Poultry Daily Log",
		filters={"name": ["in", parent_names]},
		fields=["name", "log_date", "day_of_week", "docstatus"],
		order_by="log_date desc",
	)

	flock_by_pdl = {}
	for r in flock_rows:
		flock_by_pdl.setdefault(r.parent, []).append(r)

	feed_by_pdl = {}
	for r in feed_rows:
		feed_by_pdl.setdefault(r.parent, []).append(r)

	egg_by_pdl = {}
	for r in egg_rows:
		egg_by_pdl.setdefault(r.parent, []).append(r)

	sales_by_pdl = {}
	for r in sales_rows:
		sales_by_pdl.setdefault(r.parent, []).append(r)

	result = []
	for pdl in pdl_docs:
		pdl_id = pdl.name
		flocks = flock_by_pdl.get(pdl_id, [])
		feeds = feed_by_pdl.get(pdl_id, [])
		eggs = egg_by_pdl.get(pdl_id, [])
		sales = sales_by_pdl.get(pdl_id, [])

		shed_names = sorted(list({r.shed for r in (flocks + feeds + eggs + sales) if r.get("shed")}))
		shed_display = ", ".join(shed_names) if shed_names else ""
		week_days = sorted(list({r.week_day for r in (flocks + feeds + eggs + sales) if r.get("week_day")}))
		week_day_display = ", ".join(week_days) if week_days else ""

		total_dead = sum(cint(r.get("dead")) for r in flocks)
		total_culled = sum(cint(r.get("culled")) for r in flocks)
		opening_birds = flocks[0].opening_birds if flocks else 0
		closing_birds = flocks[0].closing_birds if flocks else 0

		total_feed_kg = sum(flt(r.get("feed_spent_kg")) for r in feeds)
		total_feed_cost = sum(flt(r.get("total_feed_cost")) for r in feeds)
		feed_items = ", ".join(sorted(list({r.feed_item for r in feeds if r.get("feed_item")})))

		total_eggs_count = sum(cint(r.get("total_eggs")) for r in eggs)
		total_good_eggs = sum(cint(r.get("good_eggs")) for r in eggs)
		total_broken_eggs = sum(cint(r.get("broken_eggs")) for r in eggs)
		total_double_yolk = sum(cint(r.get("double_yolk_eggs")) for r in eggs)
		tray_summary = eggs[0].tray_summary if eggs else ""
		egg_production_pct = eggs[0].egg_production_pct if eggs else 0.0

		total_sales_amt = sum(flt(r.get("total_amount")) for r in sales)

		result.append(
			{
				"log_name": pdl_id,
				"log_date": str(pdl.log_date),
				"day_of_week": pdl.get("day_of_week") or "",
				"docstatus": pdl.docstatus,
				"shed": shed_display,
				"week_day": week_day_display,
				"opening_birds": opening_birds,
				"mortality": total_dead,
				"culled": total_culled,
				"closing_birds": closing_birds,
				"flock_details": flocks,
				"feed_item": feed_items,
				"feed_consumed_kg": total_feed_kg,
				"feed_cost": total_feed_cost,
				"feed_details": feeds,
				"total_eggs": total_eggs_count,
				"good_eggs": total_good_eggs,
				"broken_eggs": total_broken_eggs,
				"double_yolk_eggs": total_double_yolk,
				"tray_summary": tray_summary,
				"egg_production_pct": egg_production_pct,
				"egg_details": eggs,
				"sales": sales,
				"total_sales_amount": total_sales_amt,
			}
		)

	return result
