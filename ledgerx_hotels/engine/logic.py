"""Pure rules of the hotel module: nights, season rates, promotions, taxes, currency maths.
No database and no frappe import, so everything here is unit-tested on its own (tests/test_logic.py)."""
from datetime import date, datetime, timedelta

MEAL_FIELDS = {
	"Room Only": "rate_room_only",
	"Bed & Breakfast": "rate_bb",
	"Half Board": "rate_hb",
	"Full Board": "rate_fb",
	"All Inclusive": "rate_ai",
}

# Meal periods each plan already pays for. A guest has one included meal per period per person per day;
# snacks and drinks (all inclusive) are unlimited.
PLAN_PERIODS = {
	"Room Only": (),
	"Bed & Breakfast": ("Breakfast",),
	"Half Board": ("Breakfast", "Dinner"),
	"Full Board": ("Breakfast", "Lunch", "Dinner"),
	"All Inclusive": ("Breakfast", "Lunch", "Dinner", "Snack", "Drink"),
}
UNLIMITED_PERIODS = ("Snack", "Drink")


def to_date(v):
	if isinstance(v, datetime):
		return v.date()
	if isinstance(v, date):
		return v
	return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()


def nights_between(check_in, check_out):
	return (to_date(check_out) - to_date(check_in)).days


def night_dates(check_in, check_out):
	"""The dates a guest sleeps in the hotel: check-in day up to the day before check-out."""
	ci = to_date(check_in)
	return [ci + timedelta(days=i) for i in range(nights_between(check_in, check_out))]


def r2(x):
	return round(float(x or 0) + 1e-9, 2)


def _weekend_set(s):
	out = set()
	for p in str(s or "").replace(" ", "").split(","):
		if p.isdigit():
			out.add(int(p))
	return out


def plan_matches(plan, d, nights, source, party):
	"""Does this rate plan apply to the night `d` of a stay of `nights` nights?"""
	d = to_date(d)
	if plan.get("valid_from") and d < to_date(plan["valid_from"]):
		return False
	if plan.get("valid_to") and d > to_date(plan["valid_to"]):
		return False
	if int(plan.get("min_nights") or 0) > nights:
		return False
	at = plan.get("applicable_to") or "Public"
	if at == "Public":
		return True
	if at == source and (not plan.get("party") or plan.get("party") == party):
		return True
	return False


def plan_rank(plan, source, party):
	"""Higher wins: a plan made for this very party, then for this kind of source, then the public one;
	then the plan's own priority; then the one that starts latest (the more recent season)."""
	spec = 0
	if plan.get("applicable_to") not in (None, "", "Public"):
		spec = 2 if plan.get("party") and plan.get("party") == party else 1
	return (spec, int(plan.get("priority") or 0), str(plan.get("valid_from") or ""))


def night_rate(plan, meal_plan, d):
	field = MEAL_FIELDS.get(meal_plan)
	if not field:
		raise ValueError(f"Unknown meal plan: {meal_plan}")
	base = float(plan.get(field) or 0)
	if base <= 0:
		return 0.0
	up = float(plan.get("weekend_uplift_pct") or 0)
	if up and to_date(d).weekday() in _weekend_set(plan.get("weekend_days") or "3,4"):
		base *= 1 + up / 100.0
	return r2(base)


def price_stay(plans, check_in, check_out, meal_plan, source="Direct", party=None):
	"""One row per night: {date, rate, currency, plan}. A stay that crosses a season change is priced night by
	night. Returns [] rows with rate 0 and plan None for a night no plan covers (the caller must refuse that)."""
	nights = nights_between(check_in, check_out)
	rows = []
	for d in night_dates(check_in, check_out):
		cands = [p for p in plans if plan_matches(p, d, nights, source, party) and night_rate(p, meal_plan, d) > 0]
		if not cands:
			rows.append({"date": d, "rate": 0.0, "currency": None, "plan": None})
			continue
		best = max(cands, key=lambda p: plan_rank(p, source, party))
		rows.append({"date": d, "rate": night_rate(best, meal_plan, d), "currency": best.get("currency"), "plan": best.get("name")})
	return rows


def promo_ok(promo, check_in, nights, room_type=None, today=None):
	"""(ok, reason). Dates of the promotion are checked against the day of check-in."""
	if not promo:
		return False, "Unknown promotion code"
	if not promo.get("enabled", 1):
		return False, "The promotion is disabled"
	ci = to_date(check_in)
	if promo.get("valid_from") and ci < to_date(promo["valid_from"]):
		return False, "The promotion has not started for these dates"
	if promo.get("valid_to") and ci > to_date(promo["valid_to"]):
		return False, "The promotion has ended for these dates"
	if int(promo.get("min_nights") or 0) > nights:
		return False, "The stay is shorter than the promotion's minimum nights"
	if promo.get("room_type") and room_type and promo["room_type"] != room_type:
		return False, "The promotion does not apply to this room type"
	if int(promo.get("max_uses") or 0) and int(promo.get("used") or 0) >= int(promo["max_uses"]):
		return False, "The promotion has been used up"
	return True, ""


def promo_discount(promo, total):
	"""Discount amount for a stay total (never more than the total)."""
	if (promo.get("discount_type") or "Percent") == "Percent":
		d = total * float(promo.get("discount_value") or 0) / 100.0
	else:
		d = float(promo.get("discount_value") or 0)
	return r2(min(max(d, 0), total))


def taxes(net, service_rate=0, vat_rate=0, fee_rate=0, vat_on_service=True):
	"""Service charge, VAT and tourism fee on a net amount. Returns dict with the three and the total."""
	net = float(net or 0)
	service = r2(net * float(service_rate or 0) / 100.0)
	vat_base = net + service if vat_on_service else net
	vat = r2(vat_base * float(vat_rate or 0) / 100.0)
	fee = r2(net * float(fee_rate or 0) / 100.0)
	return {"service": service, "vat": vat, "fee": fee, "total": r2(net + service + vat + fee)}


def convert(amount, rate):
	"""`rate` = how many units of the target currency one unit of the source currency is worth."""
	return r2(float(amount or 0) * float(rate or 0))


def folio_balance(total, payments):
	"""payments: iterable of (type, amount_in_folio_currency). Deposits and payments add, refunds subtract."""
	paid = 0.0
	for typ, amt in payments:
		paid += -float(amt or 0) if typ == "Refund" else float(amt or 0)
	return {"paid": r2(paid), "balance": r2(float(total or 0) - paid)}


def cancellation_fee(first_night_rate, days_before, free_days, fee_pct):
	"""No fee when the guest cancels at least `free_days` before arrival; otherwise `fee_pct`% of the first night."""
	if days_before >= int(free_days or 0):
		return 0.0
	return r2(float(first_night_rate or 0) * float(fee_pct or 0) / 100.0)


def overlaps(a_in, a_out, b_in, b_out):
	"""Two stays overlap when each starts before the other leaves (leaving day is free for the next guest)."""
	return to_date(a_in) < to_date(b_out) and to_date(b_in) < to_date(a_out)


def included_qty(meal_plan, period, qty, persons, used_today, outlet_included=True):
	"""How many of `qty` ordered units of a meal period the guest's plan already covers today.
	persons = guests in the room; used_today = units of this period already given free today."""
	if not outlet_included or period not in PLAN_PERIODS.get(meal_plan, ()):
		return 0.0
	qty = float(qty or 0)
	if period in UNLIMITED_PERIODS:
		return qty
	left = max(float(persons or 1) - float(used_today or 0), 0.0)
	return min(qty, left)
