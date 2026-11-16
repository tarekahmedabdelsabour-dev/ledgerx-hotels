import frappe
from frappe.model.document import Document


class HousekeepingTask(Document):
	def on_update(self):
		"""Finishing a cleaning after departure makes the room clean again (unless it is being repaired)."""
		if self.status == "Done" and self.task_type in ("Cleaning After Departure", "Deep Clean"):
			if frappe.db.get_value("Hotel Room", self.room, "status") == "Dirty":
				frappe.db.set_value("Hotel Room", self.room, "status", "Clean")
