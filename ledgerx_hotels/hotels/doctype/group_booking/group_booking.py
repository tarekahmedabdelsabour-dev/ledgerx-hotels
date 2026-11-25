import frappe
from frappe import _
from frappe.model.document import Document

from ledgerx_hotels.engine import logic


class GroupBooking(Document):
	def validate(self):
		if not frappe.get_cached_doc("Hotel Settings").enable_groups:
			frappe.throw(_("Group Bookings are switched off in Hotel Settings"))
		if logic.nights_between(self.check_in, self.check_out) < 1:
			frappe.throw(_("Check-out must be after check-in"))
		self.total_rooms = sum(int(l.rooms or 0) for l in self.lines)
		for l in self.lines:
			if frappe.db.get_value("Room Type", l.room_type, "hotel") != self.hotel:
				frappe.throw(_("The room type belongs to another hotel"))

	def reservations(self):
		return frappe.get_all("Reservation", filters={"group": self.name}, fields=["name", "status", "room", "guest_name"], order_by="creation asc")

	@frappe.whitelist(methods=["POST"])
	def create_reservations(self):
		"""One draft reservation per room needed, billed to the company or agent. Priced by the company's own rate plan if it has one."""
		self.check_permission("write")
		if self.status != "Draft":
			frappe.throw(_("The group is {0}").format(_(self.status)))
		n = 0
		for l in self.lines:
			for _i in range(int(l.rooms)):
				n += 1
				frappe.get_doc({"doctype": "Reservation", "guest": self.customer, "guest_name": f"{self.group_name} {n}", "hotel": self.hotel,
					"check_in": self.check_in, "check_out": self.check_out, "room_type": l.room_type, "meal_plan": self.meal_plan,
					"currency": self.currency, "adults": l.adults, "children": l.children, "source": self.source, "source_party": self.customer,
					"bill_to": "Company or Agent", "group": self.name}).insert(ignore_permissions=True)
		self.db_set("status", "Rooms Created")
		return {"reservations": n}

	@frappe.whitelist(methods=["POST"])
	def confirm_all(self):
		"""Confirm every room of the group. All or nothing: if one room cannot be had, nothing is held."""
		self.check_permission("write")
		if self.status != "Rooms Created":
			frappe.throw(_("Create the reservations first"))
		for r in self.reservations():
			if r.status == "Draft":
				frappe.get_doc("Reservation", r.name).confirm()
		self.db_set("status", "Confirmed")
		return {"confirmed": len(self.reservations())}

	@frappe.whitelist(methods=["POST"])
	def cancel_group(self):
		self.check_permission("write")
		if self.status in ("Cancelled",):
			return
		out = []
		for r in self.reservations():
			if r.status in ("Draft", "Confirmed"):
				doc = frappe.get_doc("Reservation", r.name)
				doc.cancel_reservation()
				out.append(r.name)
			elif r.status == "Checked In":
				frappe.throw(_("{0} is already in the hotel").format(r.name))
		self.db_set("status", "Cancelled")
		return {"cancelled": out}
