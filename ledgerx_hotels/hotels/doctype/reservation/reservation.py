import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, flt, nowdate

from ledgerx_hotels.engine import availability, billing, logic, pricing

STAY_FIELDS = ("check_in", "check_out", "room_type", "hotel", "room", "meal_plan", "currency", "promotion", "source", "source_party")


class Reservation(Document):
	def validate(self):
		if not self.check_in or not self.check_out:
			return
		self.guest_name = self.guest_name or self.guest
		self.nights = logic.nights_between(self.check_in, self.check_out)
		if self.nights < 1:
			frappe.throw(_("Check-out must be after check-in"))
		rt = frappe.db.get_value("Room Type", self.room_type, ["hotel", "max_adults", "max_children"], as_dict=True)
		if rt.hotel != self.hotel:
			frappe.throw(_("The room type belongs to another hotel"))
		if flt(self.adults) > flt(rt.max_adults) or flt(self.children) > flt(rt.max_children):
			frappe.throw(_("The room type holds at most {0} adults and {1} children").format(rt.max_adults, rt.max_children))
		if self.room and frappe.db.get_value("Hotel Room", self.room, "room_type") != self.room_type:
			frappe.throw(_("The room is not of the chosen room type"))
		if self.source != "Direct" and not self.source_party:
			frappe.throw(_("Choose the company or agent"))
		if self.source == "Direct":
			self.source_party, self.bill_to = None, "Guest"
		if self.status in ("Draft",) or self.is_new():
			self.status = self.status or "Draft"
			pricing.price(self, billing.settings())
		else:
			before = self.get_doc_before_save()
			if before and self.status == before.status and self.status != "Draft" and not self.flags.get("stay_change"):
				for f in STAY_FIELDS:
					if str(before.get(f) or "") != str(self.get(f) or ""):
						frappe.throw(_("The stay can no longer be edited here. Use Change Room or Change Dates, or cancel and book again."))

	def on_trash(self):
		if self.status not in ("Draft", "Cancelled"):
			frappe.throw(_("Only draft or cancelled reservations can be deleted"))

	# ---------------------------------------------------------------- actions
	def _need(self, *statuses):
		# the stored status, under a row lock: a second click or a forged client copy cannot repeat a step
		if not self.is_new() and self.name:
			self.status = frappe.db.get_value(self.doctype, self.name, "status", for_update=True) or self.status
		if self.status not in statuses:
			frappe.throw(_("This reservation is {0}").format(_(self.status)))

	@frappe.whitelist(methods=["POST"])
	def confirm(self):
		self.check_permission("write")
		self._need("Draft")
		room = availability.assign_room(self)
		availability.lock(self.name, room, self.check_in, self.check_out)
		s = billing.settings()
		folio = frappe.get_doc({"doctype": "Guest Folio", "reservation": self.name, "guest": self.guest,
			"bill_to_customer": self.source_party if self.bill_to == "Company or Agent" and self.source_party else self.guest,
			"company": s.company, "currency": self.currency, "room": room})
		folio.insert(ignore_permissions=True)
		self.db_set({"room": room, "folio": folio.name, "status": "Confirmed"})
		if self.promotion and not self.promotion_counted:
			frappe.db.sql("update `tabHotel Promotion` set used = used + 1 where name=%s", self.promotion)
			self.db_set("promotion_counted", 1)
		self.reload()
		return {"room": room, "folio": folio.name, "deposit_required": self.deposit_required}

	@frappe.whitelist(methods=["POST"])
	def check_in_guest(self):
		self.check_permission("write")
		self._need("Confirmed")
		if logic.to_date(self.check_in) > logic.to_date(nowdate()):
			frappe.throw(_("The guest arrives on {0}: it is not the day yet").format(self.check_in))
		status = frappe.db.get_value("Hotel Room", self.room, "status")
		if status in ("Maintenance", "Out of Order"):
			frappe.throw(_("Room {0} is under maintenance. Change the room first.").format(self.room))
		folio = frappe.get_doc("Guest Folio", self.folio)
		folio.post_room_charges(self)
		self.db_set("status", "Checked In")
		return {"folio": self.folio}

	@frappe.whitelist(methods=["POST"])
	def check_out_guest(self):
		self.check_permission("write")
		self._need("Checked In")
		folio = frappe.get_doc("Guest Folio", self.folio)
		folio.reload()
		folio.finalize(bill_now=(self.bill_to == "Guest" or self.source == "Direct"))
		today = nowdate()
		if logic.to_date(self.check_out) > logic.to_date(today):
			availability.release(self.name, from_date=today)  # leaving early frees the rest of the nights
		frappe.db.set_value("Hotel Room", self.room, "status", "Dirty")
		if billing.settings().enable_operations:
			frappe.get_doc({"doctype": "Housekeeping Task", "room": self.room, "task_type": "Cleaning After Departure", "task_date": nowdate()}).insert(ignore_permissions=True)
		self.db_set("status", "Checked Out")
		self.reload()
		return {"invoice": folio.sales_invoice, "balance": folio.balance}

	def _end_without_stay(self, new_status, fee_pct_override=None):
		s = billing.settings()
		folio = frappe.get_doc("Guest Folio", self.folio) if self.folio else None
		availability.release(self.name)
		fee = 0.0
		if folio and self.nightly_rates:
			days_before = date_diff(self.check_in, nowdate())
			pct = s.cancel_fee_pct if fee_pct_override is None else fee_pct_override
			fee = logic.cancellation_fee(self.nightly_rates[0].rate_in_folio_currency, days_before, s.free_cancel_days, pct)
		if folio:
			if fee:
				folio.append("charges", {"charge_date": nowdate(), "charge_type": "Cancellation", "description": _("Cancellation fee"),
					"qty": 1, "rate": fee, "taxable": 0})
				folio.save()
				billing.invoice_folio(folio)
			else:
				folio.db_set("status", "Cancelled")
		if self.promotion and self.promotion_counted:
			frappe.db.sql("update `tabHotel Promotion` set used = greatest(used - 1, 0) where name=%s", self.promotion)
			self.db_set("promotion_counted", 0)
		self.db_set("status", new_status)
		self.reload()
		return {"fee": fee, "deposit_paid": folio.paid if folio else 0}

	@frappe.whitelist(methods=["POST"])
	def cancel_reservation(self):
		self.check_permission("write")
		self._need("Draft", "Confirmed")
		return self._end_without_stay("Cancelled")

	@frappe.whitelist(methods=["POST"])
	def mark_no_show(self):
		self.check_permission("write")
		self._need("Confirmed")
		if logic.to_date(self.check_in) >= logic.to_date(nowdate()):
			frappe.throw(_("The arrival date has not passed yet"))
		return self._end_without_stay("No Show", fee_pct_override=100)

	@frappe.whitelist(methods=["POST"])
	def change_room(self, room):
		self.check_permission("write")
		self._need("Confirmed", "Checked In")
		if frappe.db.get_value("Hotel Room", room, "room_type") != self.room_type:
			frappe.throw(_("The new room must be of the same room type. To change the type, cancel and book again."))
		start = self.check_in if self.status == "Confirmed" else max(logic.to_date(self.check_in), logic.to_date(nowdate()))
		free = availability.free_rooms(self.hotel, self.room_type, start, self.check_out, exclude_reservation=self.name)
		if room not in free and room != self.room:
			frappe.throw(_("Room {0} is not free for the remaining nights").format(frappe.db.get_value("Hotel Room", room, "room_number") or room))
		if room != self.room:
			availability.release(self.name, from_date=start)
			availability.lock(self.name, room, start, self.check_out)
			self.db_set("room", room)
			if self.folio:
				frappe.db.set_value("Guest Folio", self.folio, "room", room)
		return {"room": room}

	@frappe.whitelist(methods=["POST"])
	def change_dates(self, check_in, check_out):
		"""Move a confirmed stay (before arrival). Prices again and keeps the same room if it is free."""
		self.check_permission("write")
		self._need("Confirmed")
		old = (self.check_in, self.check_out, self.room)
		if logic.nights_between(check_in, check_out) < 1:
			frappe.throw(_("Check-out must be after check-in"))
		free = availability.free_rooms(self.hotel, self.room_type, check_in, check_out, exclude_reservation=self.name)
		if self.room not in free:
			frappe.throw(_("Room {0} is not free for the new dates").format(self.room))
		availability.release(self.name)
		availability.lock(self.name, self.room, check_in, check_out)
		self.check_in, self.check_out = check_in, check_out
		self.nights = logic.nights_between(check_in, check_out)
		pricing.price(self, billing.settings())
		self.flags.stay_change = True
		self.save(ignore_permissions=True)
		return {"nights": self.nights, "total": self.total, "was": [str(old[0]), str(old[1])]}


@frappe.whitelist()
def available_rooms(hotel, room_type, check_in, check_out):
	return [{"name": r, "room_number": frappe.db.get_value("Hotel Room", r, "room_number")}
		for r in availability.free_rooms(hotel, room_type, check_in, check_out)]
