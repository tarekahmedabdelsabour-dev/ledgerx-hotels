import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	cols = [
		{"label": _("Folio"), "fieldname": "name", "fieldtype": "Link", "options": "Guest Folio", "width": 140},
		{"label": _("Guest"), "fieldname": "guest", "fieldtype": "Link", "options": "Customer", "width": 160},
		{"label": _("Billed To"), "fieldname": "bill_to_customer", "fieldtype": "Link", "options": "Customer", "width": 160},
		{"label": _("Room"), "fieldname": "room", "fieldtype": "Link", "options": "Hotel Room", "width": 90},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
		{"label": _("Total"), "fieldname": "grand_total", "fieldtype": "Float", "width": 110},
		{"label": _("Paid"), "fieldname": "paid", "fieldtype": "Float", "width": 110},
		{"label": _("Balance"), "fieldname": "balance", "fieldtype": "Float", "width": 110},
	]
	status = ["in", ["Open", "To Bill"]] if not filters.get("status") else filters["status"]
	rows = frappe.get_all("Guest Folio", filters={"status": status}, fields=[c["fieldname"] for c in cols], order_by="creation desc")
	return cols, rows
