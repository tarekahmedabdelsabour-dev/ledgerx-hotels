import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, nowdate

MAX_DAYS = 366


def execute(filters=None):
	filters = filters or {}
	start = getdate(filters.get("from_date") or nowdate())
	end = getdate(filters.get("to_date") or add_days(start, 29))
	days = min(date_diff(end, start) + 1, MAX_DAYS)
	hotel = filters.get("hotel")
	room_filters = {"status": ["!=", "Out of Order"]}
	if hotel:
		room_filters["hotel"] = hotel
	rooms = frappe.db.count("Hotel Room", room_filters)
	cond, args = "", [start, end]
	if hotel:
		cond = " and r.hotel = %s"
		args.append(hotel)
	busy = dict(frappe.db.sql(
		f"""select l.night_date, count(*) from `tabRoom Night Lock` l join `tabHotel Room` r on r.name = l.room
		where l.night_date between %s and %s {cond} group by l.night_date""", args))
	cols = [
		{"label": _("Night"), "fieldname": "night", "fieldtype": "Date", "width": 110},
		{"label": _("Rooms"), "fieldname": "rooms", "fieldtype": "Int", "width": 90},
		{"label": _("Occupied"), "fieldname": "occupied", "fieldtype": "Int", "width": 90},
		{"label": _("Available"), "fieldname": "available", "fieldtype": "Int", "width": 90},
		{"label": _("Occupancy %"), "fieldname": "pct", "fieldtype": "Percent", "width": 110},
	]
	rows = []
	for i in range(days):
		d = add_days(start, i)
		occ = int(busy.get(d, 0))
		rows.append({"night": d, "rooms": rooms, "occupied": occ, "available": max(rooms - occ, 0), "pct": round(100.0 * occ / rooms, 1) if rooms else 0})
	chart = {"data": {"labels": [str(r["night"]) for r in rows], "datasets": [{"name": _("Occupancy %"), "values": [r["pct"] for r in rows]}]}, "type": "line"}
	return cols, rows, None, chart
