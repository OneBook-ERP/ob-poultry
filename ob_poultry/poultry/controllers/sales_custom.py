# Copyright (c) 2026, OB and contributors
# For license information, please see license.txt

import frappe


def validate_sales_order(doc, method=None):
	"""Ensure delivery date is consistently populated in all items if set in header."""
	items = doc.get("items")
	if doc.delivery_date and items and isinstance(items, list):
		for item in items:
			if not item.delivery_date or item.delivery_date != doc.delivery_date:
				item.delivery_date = doc.delivery_date

