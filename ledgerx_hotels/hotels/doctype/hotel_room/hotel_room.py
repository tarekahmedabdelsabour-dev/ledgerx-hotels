import frappe
from frappe import _
from frappe.model.document import Document


class HotelRoom(Document):
	def validate(self):
		if frappe.db.exists("Hotel Room", {"hotel": self.hotel, "room_number": self.room_number, "name": ["!=", self.name]}):
			frappe.throw(_("Room {0} already exists in this hotel").format(self.room_number))
		if frappe.db.get_value("Room Type", self.room_type, "hotel") != self.hotel:
			frappe.throw(_("The room type belongs to another hotel"))
		if not self.is_new() and self.status == "Out of Order":
			if frappe.db.exists("Room Night Lock", {"room": self.name, "night_date": [">=", frappe.utils.nowdate()]}):
				frappe.throw(_("The room has reservations from today onwards. Move them first."))
