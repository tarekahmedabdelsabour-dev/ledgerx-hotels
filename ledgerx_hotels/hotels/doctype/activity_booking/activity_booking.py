import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

from ledgerx_hotels.engine import billing, logic, postings


class ActivityBooking(Document):
	def validate(self):
		if not billing.settings().enable_activities:
			frappe.throw(_("Activities and Services are switched off in Hotel Settings"))
		if self.is_new():
			self.price()

	def price(self):
		sess = frappe.db.get_value("Activity Session", self.session, ["status", "session_date", "activity"], as_dict=True)
		if sess.status != "Open":
			frappe.throw(_("The session is {0}").format(_(sess.status)))
		if getdate(sess.session_date) < getdate(nowdate()):
			frappe.throw(_("The session date has passed"))
		if int(self.persons or 0) < 1:
			frappe.throw(_("Persons must be at least 1"))
		act = frappe.db.get_value("Hotel Activity", sess.activity, ["currency", "price", "included_in_all_inclusive"], as_dict=True)
		plan = None
		if self.reservation:
			r, folio = postings.stay_folio(self.reservation)
			self.currency, plan = folio.currency, r.meal_plan
			self.guest_name = self.guest_name or r.guest_name or r.guest
		self.included = 1 if (plan == "All Inclusive" and act.included_in_all_inclusive) else 0
		unit = 0 if self.included else postings.to_currency(act.price, act.currency, self.currency)
		self.total = logic.r2(unit * int(self.persons))

	def after_insert(self):
		"""Take the seats (the session row is locked, so two bookings cannot take the last seat together),
		then charge the room if the guest is staying."""
		s = frappe.db.get_value("Activity Session", self.session, ["capacity", "booked", "activity"], as_dict=True, for_update=True)
		if int(s.booked) + int(self.persons) > int(s.capacity):
			frappe.throw(_("Only {0} seats left in this session").format(int(s.capacity) - int(s.booked)))
		frappe.db.set_value("Activity Session", self.session, "booked", int(s.booked) + int(self.persons))
		if self.reservation:
			r, folio = postings.stay_folio(self.reservation)
			act = frappe.db.get_value("Hotel Activity", s.activity, ["activity_name", "taxable", "outlet"], as_dict=True)
			postings.add_lines(folio, [{"charge_type": "Activity", "department": postings.department_of(act.outlet) if act.outlet else "Activities",
				"outlet": act.outlet, "description": f"{act.activity_name} x {self.persons}" + (f" ({_('included')})" if self.included else ""),
				"qty": 1, "rate": self.total, "taxable": act.taxable, "included": self.included, "source_ref": self.name}])
			self.db_set("folio", folio.name)

	@frappe.whitelist()
	def pay_now(self, method):
		if self.status != "Booked" or self.reservation or self.sales_invoice:
			frappe.throw(_("This booking is not waiting for payment"))
		if not flt(self.total):
			return {"invoice": None, "amount": 0, "currency": self.currency}
		s = billing.settings()
		if not s.walkin_customer:
			frappe.throw(_("Set the Customer for Walk-in Sales in Hotel Settings first"))
		act = frappe.db.get_value("Hotel Activity", self.activity, ["activity_name", "taxable", "outlet"], as_dict=True)
		inv, amount, cur = billing.sell_now(s.walkin_customer, self.currency, [{"description": f"{act.activity_name} x {self.persons}", "qty": 1,
			"rate": self.total, "taxable": act.taxable, "department": "Activities", "outlet": act.outlet}], self.name, method)
		self.db_set("sales_invoice", inv)
		return {"invoice": inv, "amount": amount, "currency": cur}

	@frappe.whitelist()
	def cancel_booking(self):
		if self.status != "Booked":
			frappe.throw(_("The booking is {0}").format(_(self.status)))
		if self.sales_invoice:
			frappe.throw(_("The booking is already paid: cancel the invoice first"))
		if self.folio:
			folio = frappe.get_doc("Guest Folio", self.folio)
			if folio.status != "Open":
				frappe.throw(_("The folio is {0}: the charge can no longer be removed").format(_(folio.status)))
			folio.set("charges", [c for c in folio.charges if c.source_ref != self.name])
			folio.save(ignore_permissions=True)
		s = frappe.db.get_value("Activity Session", self.session, ["booked"], as_dict=True, for_update=True)
		frappe.db.set_value("Activity Session", self.session, "booked", max(int(s.booked) - int(self.persons), 0))
		self.db_set("status", "Cancelled")
