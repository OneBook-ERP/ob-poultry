# Copyright (c) 2026, OB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate


class PoultryHatch(Document):
	def validate(self):
		# Sync initial_egg_count and legacy eggs_set
		if self.get("initial_egg_count") is not None and self.get("initial_egg_count") != "":
			self.eggs_set = cint(self.initial_egg_count)
		elif self.get("eggs_set") is not None and self.get("eggs_set") != "":
			self.initial_egg_count = cint(self.eggs_set)

		initial = cint(self.initial_egg_count)

		# Validate and sync hatched_egg
		if self.get("hatched_egg") is not None and self.get("hatched_egg") != "":
			hatched = cint(self.hatched_egg)
			if hatched < 0:
				frappe.throw(_("Hatched Egg cannot be negative."))
			if initial > 0 and hatched > initial:
				frappe.throw(
					_("Hatched Egg ({0}) cannot exceed Initial Egg Count ({1}).").format(hatched, initial)
				)
			self.remaining_eggs = max(0, initial - hatched)
			self.initial_bird_count = hatched
			self.actual_chicks = hatched
		else:
			# Fallback for legacy records or when hatched_egg is not set
			if self.get("initial_bird_count"):
				self.hatched_egg = cint(self.initial_bird_count)
				self.actual_chicks = cint(self.initial_bird_count)
			elif self.get("actual_chicks"):
				self.hatched_egg = cint(self.actual_chicks)
				self.initial_bird_count = cint(self.actual_chicks)

			if self.get("hatched_egg"):
				self.remaining_eggs = max(0, initial - cint(self.hatched_egg))
			else:
				self.remaining_eggs = 0

		# Validate range for move_to_stock and wasted_eggs
		rem = cint(self.remaining_eggs)
		move_stock = cint(self.move_to_stock or 0)
		wasted = cint(self.wasted_eggs or 0)

		if move_stock < 0:
			frappe.throw(_("Move to Stock cannot be negative."))
		if wasted < 0:
			frappe.throw(_("Wasted Eggs cannot be negative."))

		if move_stock > rem:
			frappe.throw(_("Move to Stock ({0}) cannot exceed Remaining Eggs ({1}).").format(move_stock, rem))
		if wasted > rem:
			frappe.throw(_("Wasted Eggs ({0}) cannot exceed Remaining Eggs ({1}).").format(wasted, rem))
		if (move_stock + wasted) > rem:
			frappe.throw(
				_(
					"Sum of Move to Stock ({0}) and Wasted Eggs ({1}) cannot exceed Remaining Eggs ({2})."
				).format(move_stock, wasted, rem)
			)

		if self.get("standard_hatchability_pct") and self.get("eggs_set"):
			self.estimated_chicks = round(flt(self.eggs_set) * flt(self.standard_hatchability_pct) / 100)
		elif self.get("estimated_chicks") is not None and not self.get("standard_hatchability_pct"):
			self.estimated_chicks = None


@frappe.whitelist()
def transfer_chicks(
	hatch_name: str,
	shed: str,
	feed_warehouse: str | None = None,
	bird_count: int | None = None,
) -> dict:
	"""Creates a new Poultry Batch and submits a Poultry Chick Transfer for the hatch."""
	if not hatch_name or not frappe.db.exists("Poultry Hatch", hatch_name):
		frappe.throw(_("Invalid or missing Hatch: {0}").format(hatch_name))

	if not shed or not frappe.db.exists("Poultry Shed", shed):
		frappe.throw(_("Please select a valid destination Shed to transfer."))

	hatch = frappe.get_doc("Poultry Hatch", hatch_name)

	# Determine count to transfer
	count = (
		cint(bird_count)
		or cint(hatch.get("hatched_egg"))
		or cint(hatch.get("initial_bird_count"))
		or cint(hatch.get("actual_chicks"))
		or cint(hatch.get("initial_egg_count"))
		or cint(hatch.get("eggs_set"))
	)
	if count <= 0:
		frappe.throw(_("Bird count must be greater than 0 to transfer."))

	# Fallback feed warehouse from shed if not provided
	if not feed_warehouse:
		feed_warehouse = frappe.db.get_value("Poultry Shed", shed, "default_feed_warehouse")

	# Fallback breed if not set on hatch
	breed = hatch.get("breed")
	if not breed:
		breed = frappe.db.get_value(
			"Poultry Breed",
			{"breed_type": hatch.get("breed_type")},
			"name",
		) or frappe.db.get_value("Poultry Breed", {}, "name")

	# 1. Create Poultry Batch in destination shed
	batch = frappe.get_doc(
		{
			"doctype": "Poultry Batch",
			"shed": shed,
			"feed_warehouse": feed_warehouse,
			"breed": breed,
			"breed_type": hatch.get("breed_type") or "Layer",
			"start_date": hatch.get("hatch_date") or nowdate(),
			"initial_bird_count": count,
			"current_bird_count": count,
			"source": f"Hatch: {hatch.name} ({hatch.get('hatchery') or ''})",
			"status": "Active",
		}
	)
	batch.insert(ignore_permissions=True)

	# 2. Record Poultry Chick Transfer
	transfer = frappe.get_doc(
		{
			"doctype": "Poultry Chick Transfer",
			"hatch": hatch.name,
			"batch": batch.name,
			"quantity": count,
			"transfer_date": nowdate(),
			"notes": f"Transferred to Shed {shed} (Batch: {batch.name})",
		}
	)
	transfer.insert(ignore_permissions=True)
	transfer.submit()

	# 3. Update Hatch status and link batch
	hatch.transferred_batch = batch.name
	hatch.transferred_chicks = (hatch.get("transferred_chicks") or 0) + count
	hatch.status = "Closed"
	if not hatch.get("hatched_egg"):
		hatch.hatched_egg = count
	hatch.initial_bird_count = count
	hatch.actual_chicks = count
	hatch.save(ignore_permissions=True)

	return {
		"batch": batch.name,
		"transfer": transfer.name,
		"count": count,
		"shed": shed,
	}
