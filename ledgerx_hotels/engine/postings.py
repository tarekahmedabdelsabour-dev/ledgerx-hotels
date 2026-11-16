"""Putting restaurant orders and activities on a guest's folio."""
import frappe
from frappe import _
from frappe.utils import flt, nowdate

from ledgerx_hotels.engine import currency, logic

FB_OUTLETS = ("Restaurant", "Cafe", "Bar", "Pool Bar")
ACTIVITY_OUTLETS = ("Beach", "Spa")


def department_of(outlet):
	t = frappe.db.get_value("Outlet", outlet, "outlet_type") if outlet else None
	if t in FB_OUTLETS:
		return "Food and Beverage"
	if t in ACTIVITY_OUTLETS:
		return "Activities"
	return "Other"


def stay_folio(reservation):
	"""The open folio of a guest who is in the hotel now; refuses anyone else."""
	r = frappe.db.get_value("Reservation", reservation, ["status", "folio", "meal_plan", "adults", "children", "guest", "guest_name", "room"], as_dict=True)
	if not r or r.status != "Checked In":
		frappe.throw(_("{0} is not checked in").format(reservation))
	folio = frappe.get_doc("Guest Folio", r.folio)
	if folio.status != "Open":
		frappe.throw(_("The guest's folio is {0}").format(_(folio.status)))
	return r, folio


def used_today(folio, period, outlet=None):
	"""Units of this meal period already given free today on this folio."""
	rows = frappe.get_all("Folio Charge", filters={"parent": folio.name, "included": 1, "meal_period": period, "charge_date": nowdate()}, fields=["qty"])
	return sum(flt(r.qty) for r in rows)


def add_lines(folio, lines):
	for l in lines:
		folio.append("charges", {"charge_date": nowdate(), **l})
	folio.save(ignore_permissions=True)


def to_currency(amount, from_cur, to_cur):
	return logic.convert(amount, currency.rate(from_cur, to_cur))
