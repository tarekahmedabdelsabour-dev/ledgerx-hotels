"""Money side of the hotel, on top of ERPNext's own documents - nothing is posted by hand:

  * every payment line of a folio is a Payment Entry (any currency; ERPNext books the exchange difference),
  * the bill is a Sales Invoice in the folio's currency, with service charge, VAT and tourism fee as tax lines,
  * payments received before the invoice are applied to it as advances; payments after it are allocated to it.
"""
import frappe
from frappe import _
from frappe.utils import flt, nowdate

from ledgerx_hotels.engine import currency, logic

ROOM_TYPES = ("Room", "Meal")


def settings():
	return frappe.get_cached_doc("Hotel Settings")


def _need(s, field, label):
	if not s.get(field):
		frappe.throw(_("Set {0} in Hotel Settings first").format(_(label)))
	return s.get(field)


# ------------------------------------------------------------------------------------------------ payments
def create_payment_entry(folio, row):
	"""Make and submit the Payment Entry for one folio payment line (deposit, payment or refund)."""
	s = settings()
	company = folio.company or s.company
	method = frappe.db.get_value("Hotel Payment Method", row.method, ["account", "currency", "mode_of_payment", "enabled"], as_dict=True)
	if not method or not method.enabled:
		frappe.throw(_("Payment method {0} is not available").format(row.method))
	from erpnext.accounts.party import get_party_account, get_party_account_currency

	customer = folio.bill_to_customer or folio.guest
	receivable = get_party_account("Customer", customer, company)
	base_cur = currency.company_currency(company)
	if get_party_account_currency("Customer", customer, company) != base_cur:
		frappe.throw(_("Customer {0} has a receivable account that is not in the company currency. Hotel payments need the company-currency receivable account.").format(customer))

	amount = flt(row.amount)
	conv = flt(row.exchange_rate_to_base) if row.get("exchange_rate_to_base") else currency.rate(method.currency, base_cur, row.payment_date)
	base_amount = logic.r2(amount * conv)
	exact = base_amount / amount if amount else 1.0  # makes both sides of the entry equal to the cent

	pe = frappe.new_doc("Payment Entry")
	pe.update({
		"payment_type": "Pay" if row.payment_type == "Refund" else "Receive", "company": company, "posting_date": row.payment_date or nowdate(),
		"party_type": "Customer", "party": customer, "mode_of_payment": method.mode_of_payment,
		"reference_no": f"{folio.name}-{row.idx}", "reference_date": row.payment_date or nowdate(),
		"remarks": _("Hotel folio {0} - {1}").format(folio.name, row.payment_type),
	})
	if row.payment_type == "Refund":
		pe.update({"paid_from": method.account, "paid_to": receivable, "paid_from_account_currency": method.currency,
			"paid_to_account_currency": base_cur, "paid_amount": amount, "received_amount": base_amount,
			"source_exchange_rate": exact, "target_exchange_rate": 1})
	else:
		pe.update({"paid_from": receivable, "paid_to": method.account, "paid_from_account_currency": base_cur,
			"paid_to_account_currency": method.currency, "paid_amount": base_amount, "received_amount": amount,
			"source_exchange_rate": 1, "target_exchange_rate": exact})
	if folio.sales_invoice and row.payment_type != "Deposit":
		inv = frappe.db.get_value("Sales Invoice", folio.sales_invoice, ["outstanding_amount", "currency"], as_dict=True)
		if inv and flt(inv.outstanding_amount) > 0 and row.payment_type == "Payment":
			pe.append("references", {"reference_doctype": "Sales Invoice", "reference_name": folio.sales_invoice,
				"allocated_amount": min(flt(row.amount_in_folio_currency), flt(inv.outstanding_amount))})
	pe.insert(ignore_permissions=True)
	pe.submit()
	return pe.name


# ------------------------------------------------------------------------------------------------ invoice
def _item_rows(folio, s):
	"""Invoice lines for one folio: room nights grouped by rate, everything else line by line."""
	rows, room = [], {}
	room_acc = s.room_income_account or frappe.get_cached_value("Company", folio.company, "default_income_account")
	svc_acc = s.service_income_account or room_acc
	for c in folio.charges:
		if c.charge_type in ROOM_TYPES:
			k = (c.charge_type, flt(c.rate))
			room.setdefault(k, 0.0)
			room[k] += flt(c.qty)
		else:
			rows.append({"item_code": _need(s, "service_item", "Services Item"), "qty": flt(c.qty), "rate": flt(c.rate),
				"description": f"{c.description or c.charge_type} ({folio.name})", "income_account": svc_acc})
	for (typ, rate), qty in room.items():
		rows.insert(0, {"item_code": _need(s, "room_item", "Room Night Item"), "qty": qty, "rate": rate,
			"description": f"{_(typ)} - {folio.name}", "income_account": room_acc})
	return rows


def build_invoice(customer, folios, currency_code):
	s = settings()
	_need(s, "company", "Company")
	company = s.company
	base_cur = currency.company_currency(company)
	conv = currency.rate(currency_code, base_cur, nowdate())
	inv = frappe.new_doc("Sales Invoice")
	inv.update({
		"customer": customer, "company": company, "posting_date": nowdate(), "due_date": nowdate(), "currency": currency_code,
		"conversion_rate": conv, "selling_price_list": s.selling_price_list or frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name"),
		"price_list_currency": currency_code, "plc_conversion_rate": conv, "ignore_pricing_rule": 1, "update_stock": 0,
		"allocate_advances_automatically": 1, "cost_center": s.cost_center,
		"remarks": _("Hotel folios: {0}").format(", ".join(f.name for f in folios)),
	})
	service = vat = fee = 0.0
	for f in folios:
		for r in _item_rows(f, s):
			if s.cost_center:
				r["cost_center"] = s.cost_center
			inv.append("items", r)
		service += flt(f.service_charge)
		vat += flt(f.vat)
		fee += flt(f.tourism_fee)
	for amount, field, label in ((service, "service_account", "Service Charge"), (vat, "vat_account", "VAT"), (fee, "fee_account", "Tourism Fee")):
		if amount:
			inv.append("taxes", {"charge_type": "Actual", "account_head": _need(s, field, label + " Account"), "description": _(label),
				"tax_amount": amount, "cost_center": s.cost_center})
	inv.insert(ignore_permissions=True)
	if not inv.get("advances"):
		inv.set_advances()
		inv.save(ignore_permissions=True)
	inv.submit()
	return inv.name


def invoice_folio(folio):
	"""Invoice one folio now (guest pays the bill). Returns the Sales Invoice name."""
	if folio.sales_invoice:
		return folio.sales_invoice
	if not folio.charges:
		return None
	name = build_invoice(folio.bill_to_customer or folio.guest, [folio], folio.currency)
	folio.db_set({"sales_invoice": name, "status": "Closed"})
	return name


def bill_corporate(today=None):
	"""One invoice per company and currency for every folio waiting to be billed. Returns the invoice names."""
	groups = {}
	for f in frappe.get_all("Guest Folio", filters={"status": "To Bill"}, pluck="name"):
		d = frappe.get_doc("Guest Folio", f)
		groups.setdefault((d.bill_to_customer, d.currency), []).append(d)
	out = []
	for (customer, cur), folios in groups.items():
		try:
			name = build_invoice(customer, folios, cur)
			for d in folios:
				d.db_set({"sales_invoice": name, "status": "Closed"})
			frappe.db.commit()
			out.append(name)
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"Hotel corporate invoice failed for {customer}")
	return out


@frappe.whitelist()
def bill_corporate_now():
	frappe.only_for(["Hotel Manager", "Hotel Accountant", "System Manager"])
	return bill_corporate()
