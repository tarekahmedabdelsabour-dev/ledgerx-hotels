"""Writes the workspace, sidebar and dock JSON of ledgerx_hotels. Run from the repo root."""
import json
import os
import uuid

BASE = os.path.join(os.path.dirname(__file__), "..", "ledgerx_hotels")
TS = "2026-11-16 08:00:00.000000"
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
	("Hotel Settings", "DocType", "Hotel Settings", "settings"),
	("Arrivals and Departures", "Report", "Arrivals and Departures", "plane-landing"),
	("Hotel Occupancy", "Report", "Hotel Occupancy", "bar-chart-3"),
	("Open Folios", "Report", "Open Folios", "receipt"),
]


def write(path, data):
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w", encoding="utf-8") as fh:
		json.dump(data, fh, indent=1, ensure_ascii=False)
		fh.write("\n")


def main():
	content = [{"id": uuid.uuid4().hex[:10], "type": "header", "data": {"text": '<span class="h4"><b>Hotels</b></span>', "col": 12}}]
	shortcuts = []
	for label, kind, target, _icon in ITEMS:
		content.append({"id": uuid.uuid4().hex[:10], "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
		s = {"label": label, "link_to": target, "type": kind}
		if kind == "DocType":
			s["doc_view"] = "List"
		shortcuts.append(s)
	write(os.path.join(BASE, "hotels", "workspace", "hotels", "hotels.json"), {
		"charts": [], "content": json.dumps(content), "creation": TS, "custom_blocks": [], "docstatus": 0, "doctype": "Workspace",
		"for_user": "", "hide_custom": 1, "icon": "building-2", "idx": 1, "is_hidden": 0, "label": "Hotels", "links": [], "modified": TS,
		"modified_by": "Administrator", "module": "Hotels", "name": "Hotels", "number_cards": [], "owner": "Administrator",
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
