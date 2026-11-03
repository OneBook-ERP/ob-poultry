import frappe
from frappe.model.document import Document

BREED_TYPE_WEEKS = {
	"Broiler": 7,
	"Dual Purpose": 22,
	"Breeder": 65,
	"Layer": 81,
}


@frappe.whitelist()
def get_default_days_lineup(breed_type="Broiler"):
	"""Returns day intervals lineup (from_day, to_day, age_in_days) with empty metric values."""
	breed_type = breed_type or "Broiler"
	weeks = BREED_TYPE_WEEKS.get(breed_type, 7)
	rows = []
	for w in range(1, weeks + 1):
		from_day = (w - 1) * 7
		to_day = w * 7
		rows.append({
			"from_day": from_day,
			"to_day": to_day,
			"age_in_days": f"{from_day}-{to_day}",
			"day_start": from_day,
			"day_end": to_day,
			"standard_mortality_pct": None,
			"standard_feed_per_bird_g": None,
			"standard_body_weight_g": None,
			"standard_fcr": None,
			"standard_hdep_pct": None,
		})
	return rows


def get_broiler_defaults():
	# 7 weeks / 49 days (covers broiler lifecycle 35 to 49 days, Cobb 500 / Ross 308, meat breed so HDEP=0)
	return [
		{"from_day": 0, "to_day": 7, "age_in_days": "0-7", "day_start": 0, "day_end": 7, "standard_mortality_pct": 0.8, "standard_feed_per_bird_g": 25.0, "standard_body_weight_g": 190.0, "standard_fcr": 0.92, "standard_hdep_pct": 0.0},
		{"from_day": 7, "to_day": 14, "age_in_days": "7-14", "day_start": 7, "day_end": 14, "standard_mortality_pct": 0.4, "standard_feed_per_bird_g": 50.0, "standard_body_weight_g": 460.0, "standard_fcr": 1.15, "standard_hdep_pct": 0.0},
		{"from_day": 14, "to_day": 21, "age_in_days": "14-21", "day_start": 14, "day_end": 21, "standard_mortality_pct": 0.3, "standard_feed_per_bird_g": 80.0, "standard_body_weight_g": 930.0, "standard_fcr": 1.31, "standard_hdep_pct": 0.0},
		{"from_day": 21, "to_day": 28, "age_in_days": "21-28", "day_start": 21, "day_end": 28, "standard_mortality_pct": 0.3, "standard_feed_per_bird_g": 120.0, "standard_body_weight_g": 1520.0, "standard_fcr": 1.46, "standard_hdep_pct": 0.0},
		{"from_day": 28, "to_day": 35, "age_in_days": "28-35", "day_start": 28, "day_end": 35, "standard_mortality_pct": 0.35, "standard_feed_per_bird_g": 155.0, "standard_body_weight_g": 2180.0, "standard_fcr": 1.60, "standard_hdep_pct": 0.0},
		{"from_day": 35, "to_day": 42, "age_in_days": "35-42", "day_start": 35, "day_end": 42, "standard_mortality_pct": 0.4, "standard_feed_per_bird_g": 175.0, "standard_body_weight_g": 2800.0, "standard_fcr": 1.72, "standard_hdep_pct": 0.0},
		{"from_day": 42, "to_day": 49, "age_in_days": "42-49", "day_start": 42, "day_end": 49, "standard_mortality_pct": 0.45, "standard_feed_per_bird_g": 190.0, "standard_body_weight_g": 3350.0, "standard_fcr": 1.85, "standard_hdep_pct": 0.0},
	]


def get_dual_purpose_defaults():
	# 22 weeks / 154 days (Dual Purpose breeds e.g. Kuroiler, Sasso, Rhode Island Red)
	rows = []
	for w in range(1, 23):
		from_day = (w - 1) * 7
		to_day = w * 7
		t = (w - 1) / 21.0
		wt = 110 + 2090 * (t ** 1.3)
		feed = 18 + 87 * (t ** 0.85)
		fcr = 1.05 + 1.40 * (t ** 0.9)
		if w == 1:
			mort = 0.6
		elif w == 2:
			mort = 0.3
		elif w <= 5:
			mort = 0.2
		else:
			mort = 0.12
		if w <= 18:
			hdep = 0.0
		elif w == 19:
			hdep = 15.0
		elif w == 20:
			hdep = 42.0
		elif w == 21:
			hdep = 65.0
		else:
			hdep = 75.0
		rows.append({
			"from_day": from_day,
			"to_day": to_day,
			"age_in_days": f"{from_day}-{to_day}",
			"day_start": from_day,
			"day_end": to_day,
			"standard_mortality_pct": round(mort, 2),
			"standard_feed_per_bird_g": round(feed, 1),
			"standard_body_weight_g": round(wt, 1),
			"standard_fcr": round(fcr, 2),
			"standard_hdep_pct": round(hdep, 1),
		})
	return rows


def get_breeder_defaults():
	# 65 weeks / 455 days (Broiler Breeder Cobb 500 / Ross 308, 60-65 weeks)
	rows = []
	for w in range(1, 66):
		from_day = (w - 1) * 7
		to_day = w * 7
		if w <= 22:
			t = (w - 1) / 21.0
			wt = 140 + 2110 * (t ** 1.25)
			feed = 22 + 70 * (t ** 0.9)
			fcr = 1.15 + 1.05 * t
			mort = 0.5 if w == 1 else (0.25 if w == 2 else 0.15)
		else:
			t = (w - 23) / 42.0
			wt = 2250 + 1450 * (t ** 0.7)
			feed = 92 + 70 * min(1.0, t * 3)
			fcr = 2.20 + 0.60 * t
			mort = 0.14
		if w <= 22:
			hdep = 0.0
		elif w == 23:
			hdep = 5.0
		elif w == 24:
			hdep = 25.0
		elif w == 25:
			hdep = 55.0
		elif w == 26:
			hdep = 75.0
		elif w == 27:
			hdep = 82.0
		elif w <= 34:
			hdep = 86.0
		else:
			hdep = max(50.0, 86.0 - (w - 34) * 0.9)
		rows.append({
			"from_day": from_day,
			"to_day": to_day,
			"age_in_days": f"{from_day}-{to_day}",
			"day_start": from_day,
			"day_end": to_day,
			"standard_mortality_pct": round(mort, 2),
			"standard_feed_per_bird_g": round(feed, 1),
			"standard_body_weight_g": round(wt, 1),
			"standard_fcr": round(fcr, 2),
			"standard_hdep_pct": round(hdep, 1),
		})
	return rows


def get_layer_defaults():
	# 81 weeks / 567 days (Commercial Layer Hy-Line / Lohmann Brown)
	rows = []
	for w in range(1, 82):
		from_day = (w - 1) * 7
		to_day = w * 7
		if w <= 17:
			t = (w - 1) / 16.0
			wt = 75 + 1455 * (t ** 1.2)
			feed = 12 + 76 * (t ** 0.85)
			fcr = 1.10 + 1.50 * t
			mort = 0.5 if w == 1 else (0.25 if w == 2 else 0.15)
		else:
			t = (w - 18) / 63.0
			wt = 1530 + 440 * (t ** 0.5)
			feed = 88 + 25 * min(1.0, (w - 18) / 7.0)
			fcr = 2.05 + 0.12 * t
			mort = 0.10
		if w <= 17:
			hdep = 0.0
		elif w == 18:
			hdep = 10.0
		elif w == 19:
			hdep = 38.0
		elif w == 20:
			hdep = 70.0
		elif w == 21:
			hdep = 88.0
		elif w == 22:
			hdep = 93.0
		elif w <= 30:
			hdep = 96.0
		else:
			hdep = max(75.0, 96.0 - (w - 30) * 0.35)
		rows.append({
			"from_day": from_day,
			"to_day": to_day,
			"age_in_days": f"{from_day}-{to_day}",
			"day_start": from_day,
			"day_end": to_day,
			"standard_mortality_pct": round(mort, 2),
			"standard_feed_per_bird_g": round(feed, 1),
			"standard_body_weight_g": round(wt, 1),
			"standard_fcr": round(fcr, 2),
			"standard_hdep_pct": round(hdep, 1),
		})
	return rows


@frappe.whitelist()
def get_default_benchmarks(breed_type="Broiler"):
	breed_type = breed_type or "Broiler"
	if breed_type == "Broiler":
		return get_broiler_defaults()
	elif breed_type == "Dual Purpose":
		return get_dual_purpose_defaults()
	elif breed_type == "Breeder":
		return get_breeder_defaults()
	elif breed_type == "Layer":
		return get_layer_defaults()
	return get_broiler_defaults()


@frappe.whitelist()
def get_default_benchmark_ranges(breed_type="Broiler"):
	return [r["age_in_days"] for r in get_default_benchmarks(breed_type)]


class PoultryBreed(Document):
	def validate(self):
		if not self.benchmarks:
			self.populate_default_benchmarks()
		self.update_benchmark_day_bounds()

	def populate_days_lineup(self):
		self.set("benchmarks", [])
		for row in get_default_days_lineup(self.breed_type):
			self.append("benchmarks", row)

	def populate_default_benchmarks(self):
		self.set("benchmarks", [])
		for row in get_default_benchmarks(self.breed_type):
			self.append("benchmarks", row)

	def update_benchmark_day_bounds(self):
		for row in self.benchmarks or []:
			if row.from_day is not None and row.to_day is not None:
				row.day_start = row.from_day
				row.day_end = row.to_day
				row.age_in_days = f"{row.from_day}-{row.to_day}"
			elif row.age_in_days:
				s = str(row.age_in_days).strip()
				if "-" in s:
					parts = s.split("-")
					try:
						row.from_day = int(parts[0].strip())
						row.to_day = int(parts[1].strip())
						row.day_start = row.from_day
						row.day_end = row.to_day
					except (ValueError, TypeError):
						pass
				else:
					try:
						n = int(s)
						row.from_day = n
						row.to_day = n
						row.day_start = n
						row.day_end = n
					except (ValueError, TypeError):
						pass
