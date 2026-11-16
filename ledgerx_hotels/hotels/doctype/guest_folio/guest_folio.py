import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from ledgerx_hotels.engine import billing, currency, logic


class GuestFolio(Document):
	def validate(self):
		self.recalc()

	def recalc(self):
		s = billing.settings()
		base = taxable = 0.0
		for c in self.charges:
			c.amount = logic.r2(flt(c.qty) * flt(c.rate))
			base += c.amount
			if c.taxable:
				taxable += c.amount
		t = logic.taxes(taxable, s.service_rate, s.vat_rate, s.fee_rate, bool(s.vat_on_service))
		self.net_total = logic.r2(base)
		self.service_charge, self.vat, self.tourism_fee = t["service"], t["vat"], t["fee"]
		self.grand_total = logic.r2(base + t["service"] + t["vat"] + t["fee"])
		b = logic.folio_balance(self.grand_total, [(p.payment_type, p.amount_in_folio_currency) for p in self.payments])
		self.paid, self.balance = b["paid"], b["balance"]

	def _writable(self):
		if self.status in ("Cancelled",):
			frappe.throw(_("The folio is cancelled"))

	@frappe.whitelist()
	def add_charge(self, description, rate, qty=1, charge_type="Service", service_item=None, taxable=1):
		if self.status in ("Closed", "To Bill", "Cancelled"):
			frappe.throw(_("The folio is {0}: charges can no longer be added").format(_(self.status)))
		outlet, dept = None, "Other"
		if service_item:
			from ledgerx_hotels.engine import postings

			it = frappe.db.get_value("Hotel Service Item", service_item, ["service_name", "currency", "taxable", "outlet"], as_dict=True)
			outlet = it.outlet
			dept = postings.department_of(outlet) if outlet else "Other"
			conv = currency.rate(it.currency, self.currency)
			rate = logic.convert(rate, conv)
			description = description or it.service_name
			taxable = it.taxable
		self.append("charges", {"charge_date": nowdate(), "charge_type": charge_type, "description": description, "service_item": service_item,
			"qty": flt(qty) or 1, "rate": flt(rate), "taxable": int(taxable), "department": dept, "outlet": outlet})
		self.save()
		return self.grand_total

	@frappe.whitelist()
	def add_payment(self, payment_type, method, amount, reference=None, exchange_rate=None):
		"""Receive a deposit or payment, or give a refund, in any accepted currency."""
		self._writable()
		if payment_type not in ("Deposit", "Payment", "Refund"):
			frappe.throw(_("Unknown payment type"))
		amount = flt(amount)
		if amount <= 0:
			frappe.throw(_("The amount must be above zero"))
		m = frappe.db.get_value("Hotel Payment Method", method, ["currency"], as_dict=True)
		if not m:
			frappe.throw(_("Unknown payment method"))
		d = nowdate()
		conv_folio = flt(exchange_rate) or currency.rate(m.currency, self.currency, d)
		base_cur = currency.company_currency(self.company)
		row = self.append("payments", {"payment_date": d, "payment_type": payment_type, "method": method, "pay_currency": m.currency,
			"amount": amount, "exchange_rate": conv_folio, "amount_in_folio_currency": logic.convert(amount, conv_folio), "reference": reference})
		if payment_type == "Refund" and flt(row.amount_in_folio_currency) > flt(self.paid) + 0.005:
			frappe.throw(_("A refund cannot be more than what the guest has paid"))
		self.save()
		row = self.payments[-1]
		# exchange_rate_to_base is not a stored field: the Payment Entry reads the live rate unless a manual rate was given
		if exchange_rate:
			row.exchange_rate_to_base = flt(exchange_rate) * currency.rate(self.currency, base_cur, d)
		row.payment_entry = billing.create_payment_entry(self, row)
		row.db_update()
		self.reload()
		return {"paid": self.paid, "balance": self.balance}

	def post_room_charges(self, reservation):
		"""One Room charge per night (in the billing currency), plus the promotion discount if any."""
		if self.room_charges_posted:
			return
		for n in reservation.nightly_rates:
			self.append("charges", {"charge_date": n.night_date, "charge_type": "Room", "department": "Rooms", "description": _("Room night {0}").format(n.night_date),
				"qty": 1, "rate": n.rate_in_folio_currency, "taxable": 1})
		if flt(reservation.discount):
			self.append("charges", {"charge_date": nowdate(), "charge_type": "Other", "description": _("Discount {0}").format(reservation.promotion or ""),
				"qty": 1, "rate": -flt(reservation.discount), "taxable": 1})
		self.room_charges_posted = 1
		self.save()

	def finalize(self, bill_now):
		"""At check-out: invoice now (guest pays) or leave it for the company's monthly invoice."""
		if bill_now:
			billing.invoice_folio(self)
		else:
			self.db_set("status", "To Bill")
		self.reload()
