import frappe
from frappe import _
from frappe.model.document import Document


class HotelPromotion(Document):
	def validate(self):
		if self.discount_type == "Percent" and not (0 < self.discount_value <= 100):
			frappe.throw(_("A percentage discount must be between 0 and 100"))
		if self.discount_value <= 0:
			frappe.throw(_("The discount value must be above zero"))
