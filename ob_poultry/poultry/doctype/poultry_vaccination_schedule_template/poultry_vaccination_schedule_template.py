from frappe.model.document import Document
from frappe.utils import add_days


class PoultryVaccinationScheduleTemplate(Document):
	def get_due_rows(self, batch_name, batch_start_date):
		return [
			{
				"batch": batch_name,
				"age_in_days": item.age_in_days,
				"due_date": add_days(batch_start_date, item.age_in_days),
				"vaccine_name": item.vaccine_name,
				"dose": item.dose,
				"method": item.method,
				"status": "Pending",
			}
			for item in self.items
		]
