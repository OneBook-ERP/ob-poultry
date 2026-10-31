import frappe


def sync_pdl():
	frappe.init(site="poultry.local")
	frappe.connect()

	pdl = frappe.get_doc("Poultry Daily Log", "PDL-2026-00006")
	print(f"Syncing PDL: {pdl.name}, docstatus: {pdl.docstatus}")

	# 1. Update Shed 1 entry in shed_entries to reflect 2 batches and 4,397 total birds
	for s in pdl.shed_entries:
		if s.shed == "Shed 1 - North Layer":
			s.batches_count = 2
			s.total_birds = 4397
			s.breed = "BV 300, BV 400"
			frappe.db.set_value(
				"Poultry Daily Log Shed Entry",
				s.name,
				{"batches_count": 2, "total_birds": 4397, "breed": "BV 300, BV 400"},
			)
			print(f"Updated shed entry: {s.name}")

	# 2. Check if PB-2026-00009 exists in child tables
	b9 = "PB-2026-00009"
	shed1 = "Shed 1 - North Layer"

	# Egg Entry
	if not any(e.batch == b9 for e in pdl.egg_entries):
		egg = frappe.get_doc(
			{
				"doctype": "Poultry Daily Log Egg Entry",
				"parent": pdl.name,
				"parentfield": "egg_entries",
				"parenttype": "Poultry Daily Log",
				"shed": shed1,
				"batch": b9,
				"week_day": "W0 D0",
				"instock_eggs": 0,
				"good_eggs": 0,
				"double_yolk_eggs": 0,
				"broken_eggs": 0,
				"waste_eggs": 0,
				"total_eggs": 0,
				"trays": 0,
				"eggs_left": 0,
				"tray_summary": "0 Trays, 0 Eggs",
			}
		)
		egg.insert(ignore_permissions=True)
		print("Inserted egg entry for PB-2026-00009")

	# Feed Entry
	if not any(f.batch == b9 for f in pdl.feed_entries):
		feed = frappe.get_doc(
			{
				"doctype": "Poultry Daily Log Feed Entry",
				"parent": pdl.name,
				"parentfield": "feed_entries",
				"parenttype": "Poultry Daily Log",
				"shed": shed1,
				"batch": b9,
				"week_day": "W0 D0",
				"warehouse": "Stores - P",
				"feed_item": "",
				"opening_stock_kg": 0,
				"feed_spent_kg": 0,
				"feed_spent_g_per_bird": 0,
				"currently_available_kg": 0,
				"rate_per_kg": 0,
				"total_feed_cost": 0,
			}
		)
		feed.insert(ignore_permissions=True)
		print("Inserted feed entry for PB-2026-00009")

	# Flock Entry
	if not any(fl.batch == b9 for fl in pdl.flock_entries):
		flock = frappe.get_doc(
			{
				"doctype": "Poultry Daily Log Flock Entry",
				"parent": pdl.name,
				"parentfield": "flock_entries",
				"parenttype": "Poultry Daily Log",
				"shed": shed1,
				"batch": b9,
				"week_day": "W0 D0",
				"opening_birds": 2000,
				"dead": 0,
				"culled": 0,
				"closing_birds": 2000,
			}
		)
		flock.insert(ignore_permissions=True)
		print("Inserted flock entry for PB-2026-00009")

	# Sales Entry
	if not any(sl.batch == b9 for sl in pdl.sales_entries):
		sales = frappe.get_doc(
			{
				"doctype": "Poultry Daily Log Sales Entry",
				"parent": pdl.name,
				"parentfield": "sales_entries",
				"parenttype": "Poultry Daily Log",
				"shed": shed1,
				"batch": b9,
				"week_day": "W0 D0",
				"good_eggs": 0,
				"double_yolk_eggs": 0,
				"broken_eggs": 0,
				"rate": 0,
				"total_amount": 0,
			}
		)
		sales.insert(ignore_permissions=True)
		print("Inserted sales entry for PB-2026-00009")

	frappe.db.commit()
	print("Successfully synced PDL-2026-00006!")
	frappe.destroy()


if __name__ == "__main__":
	sync_pdl()
