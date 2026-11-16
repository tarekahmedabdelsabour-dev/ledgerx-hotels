"""Who sleeps where: every night of a confirmed stay is one row in Room Night Lock, keyed room|date and unique.
Two people confirming the same room for the same night at the same moment cannot both succeed - the database refuses
the second row - so double booking is impossible whatever the screens do."""
import frappe
from frappe import _

from ledgerx_hotels.engine import logic

LOCK = "Room Night Lock"


def lock_key(room, d):
	return f"{room}|{logic.to_date(d)}"


def free_rooms(hotel, room_type, check_in, check_out, exclude_reservation=None):
	"""Rooms of the type that are free every night of the stay (rooms out of order never count)."""
	nights = logic.night_dates(check_in, check_out)
	if not nights:
		return []
	busy = frappe.db.sql(
		"""select distinct room from `tabRoom Night Lock` where night_date between %s and %s and reservation != %s""",
		(nights[0], nights[-1], exclude_reservation or ""), pluck=True)
	rooms = frappe.get_all("Hotel Room", filters={"hotel": hotel, "room_type": room_type, "status": ["!=", "Out of Order"]},
		pluck="name", order_by="room_number asc")
	return [r for r in rooms if r not in set(busy)]


def lock(reservation, room, check_in, check_out):
	"""Take every night of the stay for `room`, all or nothing."""
	sp = "hotel_lock"
	frappe.db.savepoint(sp)
	try:
		for d in logic.night_dates(check_in, check_out):
			frappe.get_doc({"doctype": LOCK, "lock_key": lock_key(room, d), "room": room, "night_date": d,
				"reservation": reservation}).insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		frappe.db.rollback(save_point=sp)
		frappe.throw(_("Room {0} is already taken for part of these dates").format(frappe.db.get_value("Hotel Room", room, "room_number") or room))


def release(reservation, from_date=None):
	if from_date:
		frappe.db.sql("delete from `tabRoom Night Lock` where reservation=%s and night_date>=%s", (reservation, from_date))
	else:
		frappe.db.sql("delete from `tabRoom Night Lock` where reservation=%s", reservation)


def assign_room(doc):
	"""The requested room if it is free, otherwise the first free room of the type."""
	free = free_rooms(doc.hotel, doc.room_type, doc.check_in, doc.check_out, exclude_reservation=doc.name)
	if doc.room:
		if doc.room not in free:
			frappe.throw(_("Room {0} is not free for these dates").format(frappe.db.get_value("Hotel Room", doc.room, "room_number") or doc.room))
		return doc.room
	if not free:
		frappe.throw(_("No free room of this type for these dates"))
	return free[0]
