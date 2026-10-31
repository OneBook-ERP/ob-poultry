import frappe

frappe.init(site="poultry.local")
frappe.connect()

doc = frappe.get_doc("Poultry Daily Log", "PDL-2026-00006")
print("shed_entries:")
for s in doc.shed_entries:
	print(
		f"  shed: {s.shed}, batches: {s.batches_count}, total_birds: {s.total_birds}, breed: {getattr(s, 'breed', None)}"
	)

print("\negg_entries:")
for e in doc.egg_entries:
	print(f"  shed: {e.shed}, batch: {e.batch}")

print("\nfeed_entries:")
for f in doc.feed_entries:
	print(f"  shed: {f.shed}, batch: {f.batch}")

print("\nflock_entries:")
for fl in doc.flock_entries:
	print(f"  shed: {fl.shed}, batch: {fl.batch}")

print("\nsales_entries:")
for sl in doc.sales_entries:
	print(f"  shed: {sl.shed}, batch: {sl.batch}")

frappe.destroy()
