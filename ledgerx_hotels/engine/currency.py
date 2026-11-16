"""Exchange rates. One place, so every multi-currency step reads the same rate in the same way."""
import frappe
from frappe import _
from frappe.utils import flt, nowdate


def rate(from_currency, to_currency, date=None):
	"""How many `to_currency` one unit of `from_currency` is worth on `date` (from Currency Exchange)."""
	if not from_currency or not to_currency or from_currency == to_currency:
		return 1.0
	from erpnext.setup.utils import get_exchange_rate

	r = flt(get_exchange_rate(from_currency, to_currency, date or nowdate()))
	if not r:
		frappe.throw(_("No exchange rate from {0} to {1}. Add it in Currency Exchange.").format(from_currency, to_currency))
	return r


def company_currency(company):
	return frappe.get_cached_value("Company", company, "default_currency")
