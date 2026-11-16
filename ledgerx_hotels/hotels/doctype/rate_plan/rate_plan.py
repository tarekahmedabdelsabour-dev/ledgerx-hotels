import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class RatePlan(Document):
	def validate(self):
		if getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Valid To is before Valid From"))
		if frappe.db.get_value("Room Type", self.room_type, "hotel") != self.hotel:
			frappe.throw(_("The room type belongs to another hotel"))
		if not any((self.rate_room_only, self.rate_bb, self.rate_hb, self.rate_fb)):
			frappe.throw(_("Enter at least one nightly rate"))
		if self.applicable_to == "Public":
			self.party = None
