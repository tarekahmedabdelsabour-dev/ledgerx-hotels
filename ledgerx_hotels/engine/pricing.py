"""Prices a reservation from the rate plans and the promotion code, in the guest's billing currency."""
import frappe
from frappe import _
from frappe.utils import flt

from ledgerx_hotels.engine import currency, logic

PLAN_FIELDS = ["name", "valid_from", "valid_to", "currency", "applicable_to", "party", "priority", "min_nights",
	"rate_room_only", "rate_bb", "rate_hb", "rate_fb", "rate_ai", "weekend_uplift_pct", "weekend_days"]


def load_plans(hotel, room_type, check_in, check_out):
	nights = logic.night_dates(check_in, check_out)
	if not nights:
		return []
	return frappe.get_all("Rate Plan", filters={"hotel": hotel, "room_type": room_type, "enabled": 1,
		"valid_to": [">=", nights[0]], "valid_from": ["<=", nights[-1]]}, fields=PLAN_FIELDS)


def promotion(doc):
	if not doc.promotion:
		return None
	return frappe.db.get_value("Hotel Promotion", doc.promotion, ["name", "enabled", "discount_type", "discount_value", "valid_from",
		"valid_to", "min_nights", "room_type", "max_uses", "used"], as_dict=True)


def price(doc, settings):
	"""Fills nightly_rates, subtotal, discount, total and deposit_required on the reservation."""
	plans = load_plans(doc.hotel, doc.room_type, doc.check_in, doc.check_out)
	party = doc.source_party if doc.source != "Direct" else None
	rows = logic.price_stay(plans, doc.check_in, doc.check_out, doc.meal_plan, doc.source or "Direct", party)
	missing = [str(r["date"]) for r in rows if not r["plan"]]
	if missing:
		frappe.throw(_("No rate plan covers these nights: {0}").format(", ".join(missing[:5]) + ("..." if len(missing) > 5 else "")))
	doc.set("nightly_rates", [])
	total = 0.0
	for r in rows:
		conv = currency.rate(r["currency"], doc.currency, r["date"])
		in_folio = logic.convert(r["rate"], conv)
		total += in_folio
		doc.append("nightly_rates", {"night_date": r["date"], "rate_plan": r["plan"], "plan_currency": r["currency"],
			"rate": r["rate"], "rate_in_folio_currency": in_folio})
	doc.subtotal = logic.r2(total)
	doc.discount = 0
	promo = promotion(doc)
	if doc.promotion:
		counted = bool(doc.get("promotion_counted"))
		check = dict(promo or {})
		if counted and check:
			check["used"] = max(0, int(check.get("used") or 0) - 1)  # this reservation's own use does not count against it
		ok, why = logic.promo_ok(check, doc.check_in, doc.nights, doc.room_type)
		if not ok:
			frappe.throw(_(why))
		doc.discount = logic.promo_discount(promo, doc.subtotal)
	doc.total = logic.r2(doc.subtotal - doc.discount)
	doc.deposit_required = logic.r2(doc.total * flt(settings.deposit_pct) / 100.0)
