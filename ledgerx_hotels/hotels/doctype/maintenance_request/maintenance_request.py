import frappe
from frappe import _
from frappe.model.document import Document


class MaintenanceRequest(Document):
	def validate(self):
		if not self.room and not self.area:
			frappe.throw(_("Choose the room or write the area"))

	def on_update(self):
		if not self.room or not self.block_room:
			return
		if self.status != "Done":
			frappe.db.set_value("Hotel Room", self.room, "status", "Maintenance")
		elif frappe.db.get_value("Hotel Room", self.room, "status") == "Maintenance":
			frappe.db.set_value("Hotel Room", self.room, "status", "Dirty")  # repaired: it still needs cleaning
