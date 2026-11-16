import frappe
from frappe import _
from frappe.utils import getdate, nowdate


def execute(filters=None):
	filters = filters or {}
	day = getdate(filters.get("date") or nowdate())
	cols = [
		{"label": _("Movement"), "fieldname": "movement", "fieldtype": "Data", "width": 110},
		{"label": _("Reservation"), "fieldname": "name", "fieldtype": "Link", "options": "Reservation", "width": 140},
		{"label": _("Guest"), "fieldname": "guest", "fieldtype": "Link", "options": "Customer", "width": 160},
		{"label": _("Room"), "fieldname": "room", "fieldtype": "Link", "options": "Hotel Room", "width": 90},
		{"label": _("Room Type"), "fieldname": "room_type", "fieldtype": "Link", "options": "Room Type", "width": 130},
		{"label": _("Check-in"), "fieldname": "check_in", "fieldtype": "Date", "width": 100},
		{"label": _("Check-out"), "fieldname": "check_out", "fieldtype": "Date", "width": 100},
		{"label": _("Adults"), "fieldname": "adults", "fieldtype": "Int", "width": 70},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("Flight"), "fieldname": "flight_no", "fieldtype": "Data", "width": 90},
	]
	fields = ["name", "guest", "room", "room_type", "check_in", "check_out", "adults", "status", "flight_no"]
	hotel = {"hotel": filters["hotel"]} if filters.get("hotel") else {}
	rows = []
	for r in frappe.get_all("Reservation", filters={**hotel, "check_in": day, "status": ["in", ["Confirmed", "Checked In"]]}, fields=fields):
		r["movement"] = _("Arrival")
		rows.append(r)
	for r in frappe.get_all("Reservation", filters={**hotel, "check_out": day, "status": "Checked In"}, fields=fields):
		r["movement"] = _("Departure")
		rows.append(r)
	return cols, rows
