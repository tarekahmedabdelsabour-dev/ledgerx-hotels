import frappe
from frappe.utils import getdate, nowdate

from ledgerx_hotels.engine import billing


def bill_corporate_daily():
	"""On the configured day of the month, invoice every company or agent for the folios waiting to be billed."""
	s = frappe.get_cached_doc("Hotel Settings")
	if getdate(nowdate()).day == (s.corporate_billing_day or 1):
		billing.bill_corporate()
