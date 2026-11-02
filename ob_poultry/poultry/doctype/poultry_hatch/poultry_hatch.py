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

		# Sync initial_bird_count and legacy actual_chicks
		if self.get("initial_bird_count") is not None and self.get("initial_bird_count") != "":
			self.actual_chicks = cint(self.initial_bird_count)
		elif self.get("actual_chicks") is not None and self.get("actual_chicks") != "":
			self.initial_bird_count = cint(self.actual_chicks)

		if self.get("standard_hatchability_pct") and self.get("eggs_set"):
			self.estimated_chicks = round(flt(self.eggs_set) * flt(self.standard_hatchability_pct) / 100)
		else:
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
	if not hatch.get("initial_bird_count"):
		hatch.initial_bird_count = count
		hatch.actual_chicks = count
	hatch.save(ignore_permissions=True)

	return {
		"batch": batch.name,
		"transfer": transfer.name,
		"count": count,
		"shed": shed,
	}
