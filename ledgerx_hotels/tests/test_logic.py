"""Pure-logic tests: run with `python3 -m unittest ledgerx_hotels.tests.test_logic` (no site needed)."""
import importlib.util
import os
import unittest

_p = os.path.join(os.path.dirname(__file__), "..", "engine", "logic.py")
_spec = importlib.util.spec_from_file_location("hotel_logic", _p)
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

SUMMER = {"name": "SUM", "valid_from": "2026-06-01", "valid_to": "2026-09-30", "currency": "USD", "rate_room_only": 100,
	"rate_bb": 120, "applicable_to": "Public", "weekend_uplift_pct": 10, "weekend_days": "3,4", "priority": 0}
WINTER = {"name": "WIN", "valid_from": "2026-10-01", "valid_to": "2027-05-31", "currency": "USD", "rate_room_only": 80,
	"rate_bb": 95, "applicable_to": "Public", "priority": 0}
CORP = {"name": "CORP", "valid_from": "2026-01-01", "valid_to": "2027-12-31", "currency": "EGP", "rate_room_only": 3000,
	"applicable_to": "Corporate", "party": "ACME", "priority": 0}
AGENT = {"name": "AG", "valid_from": "2026-01-01", "valid_to": "2027-12-31", "currency": "USD", "rate_room_only": 70,
	"applicable_to": "Agent", "priority": 0}


class T(unittest.TestCase):
	def test_nights_and_dates(self):
		self.assertEqual(L.nights_between("2026-07-01", "2026-07-04"), 3)
		self.assertEqual([str(d) for d in L.night_dates("2026-07-01", "2026-07-03")], ["2026-07-01", "2026-07-02"])
		self.assertEqual(L.night_dates("2026-07-01", "2026-07-01"), [])

	def test_overlap_leaving_day_is_free(self):
		self.assertFalse(L.overlaps("2026-07-01", "2026-07-03", "2026-07-03", "2026-07-05"))
		self.assertTrue(L.overlaps("2026-07-01", "2026-07-04", "2026-07-03", "2026-07-05"))

	def test_rate_per_night_with_weekend_uplift(self):
		# 2026-07-02 is a Thursday (weekday 3): +10%
		rows = L.price_stay([SUMMER], "2026-07-01", "2026-07-03", "Room Only")
		self.assertEqual([r["rate"] for r in rows], [100.0, 110.0])

	def test_season_change_is_priced_per_night(self):
		rows = L.price_stay([SUMMER, WINTER], "2026-09-29", "2026-10-02", "Bed & Breakfast")
		self.assertEqual([(r["plan"], r["rate"]) for r in rows], [("SUM", 120.0), ("SUM", 120.0), ("WIN", 95.0)])

	def test_uncovered_night_has_no_plan(self):
		rows = L.price_stay([SUMMER], "2026-05-31", "2026-06-02", "Room Only")
		self.assertIsNone(rows[0]["plan"])
		self.assertEqual(rows[1]["plan"], "SUM")

	def test_specific_plan_beats_public(self):
		r = L.price_stay([SUMMER, CORP, AGENT], "2026-07-01", "2026-07-02", "Room Only", "Corporate", "ACME")[0]
		self.assertEqual((r["plan"], r["currency"]), ("CORP", "EGP"))
		r = L.price_stay([SUMMER, CORP, AGENT], "2026-07-01", "2026-07-02", "Room Only", "Corporate", "OTHER")[0]
		self.assertEqual(r["plan"], "SUM")
		r = L.price_stay([SUMMER, CORP, AGENT], "2026-07-01", "2026-07-02", "Room Only", "Agent", "X")[0]
		self.assertEqual(r["plan"], "AG")

	def test_min_nights(self):
		p = dict(SUMMER, name="LONG", rate_room_only=60, min_nights=7, priority=5)
		self.assertEqual(L.price_stay([SUMMER, p], "2026-07-01", "2026-07-03", "Room Only")[0]["plan"], "SUM")
		self.assertEqual(L.price_stay([SUMMER, p], "2026-07-01", "2026-07-09", "Room Only")[0]["plan"], "LONG")

	def test_promotion(self):
		pr = {"enabled": 1, "discount_type": "Percent", "discount_value": 15, "valid_from": "2026-06-01", "valid_to": "2026-08-31", "min_nights": 3}
		self.assertTrue(L.promo_ok(pr, "2026-07-01", 3)[0])
		self.assertFalse(L.promo_ok(pr, "2026-07-01", 2)[0])
		self.assertFalse(L.promo_ok(pr, "2026-09-01", 3)[0])
		self.assertEqual(L.promo_discount(pr, 1000), 150.0)
		self.assertEqual(L.promo_discount({"discount_type": "Amount", "discount_value": 5000}, 1000), 1000.0)
		self.assertFalse(L.promo_ok(dict(pr, max_uses=2, used=2), "2026-07-01", 3)[0])
		self.assertFalse(L.promo_ok(None, "2026-07-01", 3)[0])

	def test_taxes(self):
		t = L.taxes(1000, 12, 14, 1, True)
		self.assertEqual((t["service"], t["vat"], t["fee"], t["total"]), (120.0, 156.8, 10.0, 1286.8))
		t = L.taxes(1000, 12, 14, 0, False)
		self.assertEqual((t["vat"], t["total"]), (140.0, 1260.0))

	def test_currency_and_balance(self):
		self.assertEqual(L.convert(100, 48.5), 4850.0)
		b = L.folio_balance(5000, [("Deposit", 1000), ("Payment", 3000), ("Refund", 200)])
		self.assertEqual((b["paid"], b["balance"]), (3800.0, 1200.0))

	def test_cancellation_fee(self):
		self.assertEqual(L.cancellation_fee(100, 5, 3, 100), 0.0)
		self.assertEqual(L.cancellation_fee(100, 1, 3, 100), 100.0)
		self.assertEqual(L.cancellation_fee(100, 0, 3, 50), 50.0)


if __name__ == "__main__":
	unittest.main()
