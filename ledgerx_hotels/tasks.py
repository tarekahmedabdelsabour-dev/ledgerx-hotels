import frappe
from frappe.utils import getdate, nowdate

from ledgerx_hotels.engine import billing


def bill_corporate_daily():
	"""On the configured day of the month, invoice every company or agent for the folios waiting to be billed."""
	s = frappe.get_cached_doc("Hotel Settings")
	if getdate(nowdate()).day == (s.corporate_billing_day or 1):
		billing.bill_corporate()


def daily_cleaning():
	"""Every morning: a cleaning task for each room with a guest in it."""
	s = frappe.get_cached_doc("Hotel Settings")
	if not s.enable_operations:
		return
	today = nowdate()
	for room in frappe.get_all("Reservation", filters={"status": "Checked In"}, pluck="room"):
		if room and not frappe.db.exists("Housekeeping Task", {"room": room, "task_date": today, "task_type": "Daily Cleaning"}):
			frappe.get_doc({"doctype": "Housekeeping Task", "room": room, "task_type": "Daily Cleaning", "task_date": today}).insert(ignore_permissions=True)
