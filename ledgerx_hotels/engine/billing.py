"""Money side of the hotel, on top of ERPNext's own documents - nothing is posted by hand:

  * every payment line of a folio is a Payment Entry (any currency; ERPNext books the exchange difference),
  * the bill is a Sales Invoice in the folio's currency, with service charge, VAT and tourism fee as tax lines,
  * payments received before the invoice are applied to it as advances; payments after it are allocated to it.
"""
import frappe
from frappe import _
from frappe.utils import flt, nowdate

from ledgerx_hotels.engine import currency, logic



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
def _department_account(s, charge, outlet, company):
	"""Revenue account: the outlet's own, else the department's, else the company default."""
	dept = charge.get("department") or "Other"
	acc = None
	if dept == "Rooms":
		acc = s.room_income_account
	elif dept == "Food and Beverage":
		acc = (outlet and outlet.income_account) or s.fb_income_account
	elif dept == "Activities":
		acc = (outlet and outlet.income_account) or s.activities_income_account
	return acc or s.service_income_account or s.room_income_account or frappe.get_cached_value("Company", company, "default_income_account")


def _item_rows(folio, s):
	"""Invoice lines for one folio: room nights grouped by rate, everything else line by line.
	Charges the meal plan already covers (rate 0) are not invoiced."""
	rows, room = [], {}
	for c in folio.charges:
		if c.get("included") or (flt(c.rate) == 0 and flt(c.amount) == 0):
			continue
		outlet = frappe.db.get_value("Outlet", c.outlet, ["income_account", "cost_center"], as_dict=True) if c.get("outlet") else None
		acc = _department_account(s, c, outlet, folio.company)
		cc = (outlet and outlet.cost_center) or s.cost_center
		if c.charge_type == "Room":
			room.setdefault((flt(c.rate), acc, cc), 0.0)
			room[(flt(c.rate), acc, cc)] += flt(c.qty)
		else:
			rows.append({"item_code": _need(s, "service_item", "Services Item"), "qty": flt(c.qty), "rate": flt(c.rate),
				"description": f"{c.description or c.charge_type} ({folio.name})", "income_account": acc, "cost_center": cc})
	for (rate, acc, cc), qty in room.items():
		rows.insert(0, {"item_code": _need(s, "room_item", "Room Night Item"), "qty": qty, "rate": rate,
			"description": f"{_('Room')} - {folio.name}", "income_account": acc, "cost_center": cc})
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
			if not r.get("cost_center") and s.cost_center:
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


def sell_now(customer, currency_code, lines, tag, method, company=None):
	"""A sale to someone who is not staying: invoice now and receive the money at once in `method`'s currency.
	lines: dicts with description, qty, rate, taxable, department, outlet. Returns (invoice, amount paid, method currency)."""
	s = settings()
	company = company or s.company
	taxable = sum(flt(l["qty"]) * flt(l["rate"]) for l in lines if l.get("taxable", 1))
	net = sum(flt(l["qty"]) * flt(l["rate"]) for l in lines)
	tx = logic.taxes(taxable, s.service_rate, s.vat_rate, s.fee_rate, bool(s.vat_on_service))
	pseudo = frappe._dict(name=tag, company=company, currency=currency_code, service_charge=tx["service"], vat=tx["vat"], tourism_fee=tx["fee"],
		charges=[frappe._dict(charge_type="Service", department=l.get("department") or "Other", outlet=l.get("outlet"), description=l["description"],
			qty=flt(l["qty"]), rate=flt(l["rate"]), amount=logic.r2(flt(l["qty"]) * flt(l["rate"])), included=0) for l in lines])
	inv = build_invoice(customer, [pseudo], currency_code)
	total = logic.r2(net + tx["service"] + tx["vat"] + tx["fee"])
	m = frappe.db.get_value("Hotel Payment Method", method, ["currency"], as_dict=True)
	to_method = currency.rate(currency_code, m.currency, nowdate())
	amount = logic.convert(total, to_method)
	row = frappe._dict(idx=1, payment_type="Payment", payment_date=nowdate(), method=method, amount=amount, amount_in_folio_currency=total)
	folio = frappe._dict(name=tag, company=company, bill_to_customer=customer, guest=customer, sales_invoice=inv, currency=currency_code)
	create_payment_entry(folio, row)
	return inv, amount, m.currency
