"""Writes the workspace, sidebar and dock JSON of ledgerx_hotels. Run from the repo root."""
import json
import os
import uuid

BASE = os.path.join(os.path.dirname(__file__), "..", "ledgerx_hotels")
TS = "2026-11-16 12:30:00.000000"  # raise this whenever the workspace changes: migrate only re-reads a file that is newer than the saved one
CARDS = [  # (label, doctype, filters, function, fn_field)
	("Arrivals Today", "Reservation", [["Reservation", "check_in", "Timespan", "today"], ["Reservation", "status", "in", ["Confirmed", "Checked In"]]], "Count", None),
	("Departures Today", "Reservation", [["Reservation", "check_out", "Timespan", "today"], ["Reservation", "status", "=", "Checked In"]], "Count", None),
	("In-House Guests", "Reservation", [["Reservation", "status", "=", "Checked In"]], "Count", None),
	("Open Folios", "Guest Folio", [["Guest Folio", "status", "in", ["Open", "To Bill"]]], "Count", None),
	("Rooms to Clean", "Hotel Room", [["Hotel Room", "status", "=", "Dirty"]], "Count", None),
	("Open Maintenance", "Maintenance Request", [["Maintenance Request", "status", "!=", "Done"]], "Count", None),
	("Restaurant Orders Today", "Outlet Order", [["Outlet Order", "order_time", "Timespan", "today"], ["Outlet Order", "status", "!=", "Cancelled"]], "Count", None),
	("Activity Bookings Today", "Activity Booking", [["Activity Booking", "session_date", "Timespan", "today"], ["Activity Booking", "status", "=", "Booked"]], "Count", None),
]
CHARTS = [  # (name, doctype, type, kind, extra)
	("Reservations per Month", "Reservation", "Bar", "series", {"based_on": "creation", "filters": [["Reservation", "status", "!=", "Cancelled"]]}),
	("Reservations by Status", "Reservation", "Donut", "group", {"by": "status"}),
	("Rooms by Status", "Hotel Room", "Donut", "group", {"by": "status"}),
	("Restaurant Orders per Month", "Outlet Order", "Bar", "series", {"based_on": "order_time", "filters": [["Outlet Order", "status", "!=", "Cancelled"]]}),
]
ITEMS = [  # (label, kind, target, icon)
	("Reservation", "DocType", "Reservation", "calendar-check"),
	("Guest Folio", "DocType", "Guest Folio", "file-text"),
	("Hotel Room", "DocType", "Hotel Room", "key-round"),
	("Room Type", "DocType", "Room Type", "bed-double"),
	("Hotel", "DocType", "Hotel", "building-2"),
	("Rate Plan", "DocType", "Rate Plan", "tags"),
	("Hotel Promotion", "DocType", "Hotel Promotion", "percent"),
	("Hotel Service Item", "DocType", "Hotel Service Item", "concierge-bell"),
	("Hotel Payment Method", "DocType", "Hotel Payment Method", "banknote"),
	("Outlet", "DocType", "Outlet", "utensils"),
	("Outlet Order", "DocType", "Outlet Order", "shopping-basket"),
	("Hotel Activity", "DocType", "Hotel Activity", "life-buoy"),
	("Activity Session", "DocType", "Activity Session", "clock"),
	("Activity Booking", "DocType", "Activity Booking", "ticket"),
	("Group Booking", "DocType", "Group Booking", "users"),
	("Housekeeping Task", "DocType", "Housekeeping Task", "spray-can"),
	("Maintenance Request", "DocType", "Maintenance Request", "wrench"),
	("Guest Request", "DocType", "Guest Request", "message-square"),
	("Hotel Settings", "DocType", "Hotel Settings", "settings"),
	("Revenue by Department", "Report", "Revenue by Department", "pie-chart"),
	("Arrivals and Departures", "Report", "Arrivals and Departures", "plane-landing"),
	("Hotel Occupancy", "Report", "Hotel Occupancy", "bar-chart-3"),
	("Open Folios", "Report", "Open Folios", "receipt"),
]


def write(path, data):
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w", encoding="utf-8") as fh:
		json.dump(data, fh, indent=1, ensure_ascii=False)
		fh.write("\n")


def slug(n):
	return n.lower().replace(" ", "_").replace("-", "_")


def write_cards():
	for label, dt, flt, fn, _f in CARDS:
		write(os.path.join(BASE, "hotels", "number_card", slug(label), slug(label) + ".json"), {
			"creation": TS, "docstatus": 0, "doctype": "Number Card", "document_type": dt, "filters_json": json.dumps(flt), "function": fn,
			"idx": 0, "is_public": 1, "is_standard": 1, "label": label, "modified": TS, "modified_by": "Administrator", "module": "Hotels",
			"name": label, "owner": "Administrator", "show_percentage_stats": 0, "stats_time_interval": "Daily", "type": "Document Type"})
	for name, dt, typ, kind, x in CHARTS:
		d = {"chart_name": name, "creation": TS, "docstatus": 0, "doctype": "Dashboard Chart", "document_type": dt, "dynamic_filters_json": "",
			"idx": 0, "is_public": 1, "is_standard": 1, "modified": TS, "modified_by": "Administrator", "module": "Hotels", "name": name,
			"number_of_groups": 0, "owner": "Administrator", "type": typ, "use_report_chart": 0, "y_axis": []}
		if kind == "group":
			d.update({"chart_type": "Group By", "group_by_based_on": x["by"], "group_by_type": "Count", "filters_json": "[]", "timeseries": 0})
		else:
			d.update({"chart_type": "Count", "based_on": x["based_on"], "filters_json": json.dumps(x["filters"]), "time_interval": "Monthly",
				"timeseries": 1, "timespan": "Last Year"})
		write(os.path.join(BASE, "hotels", "dashboard_chart", slug(name), slug(name) + ".json"), d)


def main():
	write_cards()
	content = [{"id": uuid.uuid4().hex[:10], "type": "header", "data": {"text": '<span class="h4"><b>Hotels</b></span>', "col": 12}}]
	for label, *_r in CARDS:
		content.append({"id": uuid.uuid4().hex[:10], "type": "number_card", "data": {"number_card_name": label, "col": 3}})
	for name, *_r in CHARTS:
		content.append({"id": uuid.uuid4().hex[:10], "type": "chart", "data": {"chart_name": name, "col": 6}})
	shortcuts = []
	for label, kind, target, _icon in ITEMS:
		content.append({"id": uuid.uuid4().hex[:10], "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
		s = {"label": label, "link_to": target, "type": kind}
		if kind == "DocType":
			s["doc_view"] = "List"
		shortcuts.append(s)
	write(os.path.join(BASE, "hotels", "workspace", "hotels", "hotels.json"), {
		"charts": [{"chart_name": c[0], "label": c[0]} for c in CHARTS], "content": json.dumps(content), "creation": TS, "custom_blocks": [], "docstatus": 0, "doctype": "Workspace",
		"for_user": "", "hide_custom": 1, "icon": "building-2", "idx": 1, "is_hidden": 0, "label": "Hotels", "links": [], "title": "Hotels", "modified": TS,
		"modified_by": "Administrator", "module": "Hotels", "name": "Hotels", "number_cards": [{"label": c[0], "number_card_name": c[0]} for c in CARDS], "owner": "Administrator",
		"parent_page": "", "public": 1, "quick_lists": [], "roles": [], "sequence_id": 21.0, "shortcuts": shortcuts})
	items = [{"child": 0, "collapsible": 1, "doctype": "Sidebar Item", "icon": "house", "idx": 1, "indent": 0, "keep_closed": 0, "label": "Home",
		"link_to": "Hotels", "link_type": "Workspace", "parentfield": "items", "parenttype": "Sidebar", "show_arrow": 0, "type": "Link"}]
	for i, (label, kind, target, icon) in enumerate(ITEMS, start=2):
		items.append({"child": 0, "collapsible": 1, "doctype": "Sidebar Item", "icon": icon, "idx": i, "indent": 0, "keep_closed": 0,
			"label": label, "link_to": target, "link_type": kind, "parentfield": "items", "parenttype": "Sidebar", "show_arrow": 0, "type": "Link"})
	write(os.path.join(BASE, "sidebar", "hotels", "hotels.json"), {"app": "ledgerx_hotels", "doctype": "Sidebar", "header_icon": "building-2",
		"items": items, "module": "Hotels", "name": "Hotels", "standard": 1, "title": "Hotels"})
	write(os.path.join(BASE, "dock", "hotels", "hotels.json"), {"app": "ledgerx_hotels", "creation": TS, "docstatus": 0, "doctype": "Dock", "idx": 0,
		"items": [{"added": 0, "hidden": 0, "icon": "building-2", "link_to": "Hotels", "link_type": "Sidebar", "title": "Hotels"}],
		"modified": TS, "modified_by": "Administrator", "name": "hotels", "owner": "Administrator", "standard": 1})


main()
