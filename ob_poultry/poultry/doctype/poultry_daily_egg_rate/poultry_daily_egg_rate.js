// Copyright (c) 2026, OB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Poultry Daily Egg Rate", {
	refresh(frm) {
		// Read-only indicator of sync
		if (frm.doc.synced_at) {
			frm.set_intro(__("Synced from {0} at {1}", [frm.doc.source || "MKisan API", frm.doc.synced_at]), "green");
		}
	}
});
