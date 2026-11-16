import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from ledgerx_hotels.engine import billing, logic, postings


class OutletOrder(Document):
	def validate(self):
		if not billing.settings().enable_fb:
			frappe.throw(_("Restaurants and Bars are switched off in Hotel Settings"))
		if not self.items:
			frappe.throw(_("Add at least one item"))
		if self.status != "Open" and not self.is_new():
			before = self.get_doc_before_save()
			if before and before.status == self.status and not self.flags.get("internal"):
				frappe.throw(_("The order is {0} and can no longer be changed").format(_(self.status)))
			return
		outlet = frappe.db.get_value("Outlet", self.outlet, ["hotel", "enabled", "included_in_meal_plans"], as_dict=True)
		if not outlet.enabled:
			frappe.throw(_("The outlet is not enabled"))
		plan, folio = None, None
		if self.reservation:
			r, folio = postings.stay_folio(self.reservation)
			self.currency = folio.currency
			self.guest_name = r.guest_name or r.guest
			plan = r.meal_plan
		given = {}
		net = 0.0
		for row in self.items:
			it = frappe.db.get_value("Hotel Service Item", row.service_item, ["currency", "default_rate", "meal_period", "outlet"], as_dict=True)
			if it.outlet and it.outlet != self.outlet:
				frappe.throw(_("{0} is not sold at {1}").format(row.service_item, self.outlet))
			row.rate = postings.to_currency(it.default_rate, it.currency, self.currency)
			row.meal_period = it.meal_period
			free = 0.0
			if plan and it.meal_period and it.meal_period != "Any":
				persons = max(int(self.persons or 1), 1)
				prior = postings.used_today(folio, it.meal_period) + given.get(it.meal_period, 0.0)
				free = logic.included_qty(plan, it.meal_period, row.qty, persons, prior, bool(outlet.included_in_meal_plans))
				given[it.meal_period] = given.get(it.meal_period, 0.0) + free
			row.included_qty = free
			row.amount = logic.r2((flt(row.qty) - free) * flt(row.rate))
			net += row.amount
		self.net_total = logic.r2(net)

	def _need_open(self):
		if self.status != "Open":
			frappe.throw(_("The order is {0}").format(_(self.status)))

	@frappe.whitelist()
	def post_to_room(self):
		"""Charge the order to the room: what the plan covers goes in at zero, the rest at the item's price."""
		self._need_open()
		if not self.reservation:
			frappe.throw(_("Choose the room first, or take payment on the spot"))
		r, folio = postings.stay_folio(self.reservation)
		dept = postings.department_of(self.outlet)
		lines = []
		for row in self.items:
			it = frappe.db.get_value("Hotel Service Item", row.service_item, ["service_name", "taxable"], as_dict=True)
			base = {"charge_type": "Meal" if row.meal_period in ("Breakfast", "Lunch", "Dinner", "Snack") else "Service", "department": dept,
				"outlet": self.outlet, "source_ref": self.name, "taxable": it.taxable}
			if flt(row.included_qty):
				lines.append({**base, "description": f"{it.service_name} ({_('included')})", "qty": row.included_qty, "rate": 0, "included": 1, "meal_period": row.meal_period})
			rest = flt(row.qty) - flt(row.included_qty)
			if rest > 0:
				lines.append({**base, "description": it.service_name, "qty": rest, "rate": row.rate})
		postings.add_lines(folio, lines)
		self.flags.internal = True
		self.db_set({"status": "Posted to Room", "folio": folio.name})
		self.issue_stock()
		return {"folio": folio.name, "total": self.net_total}

	@frappe.whitelist()
	def pay_now(self, method):
		"""Someone who is not staying pays on the spot, in any accepted currency."""
		self._need_open()
		if self.reservation:
			frappe.throw(_("This order belongs to a room: post it to the room"))
		s = billing.settings()
		if not s.walkin_customer:
			frappe.throw(_("Set the Customer for Walk-in Sales in Hotel Settings first"))
		lines = []
		for row in self.items:
			it = frappe.db.get_value("Hotel Service Item", row.service_item, ["service_name", "taxable"], as_dict=True)
			lines.append({"description": it.service_name, "qty": row.qty, "rate": row.rate, "taxable": it.taxable,
				"department": postings.department_of(self.outlet), "outlet": self.outlet})
		inv, amount, cur = billing.sell_now(s.walkin_customer, self.currency, lines, self.name, method)
		self.flags.internal = True
		self.db_set({"status": "Paid", "sales_invoice": inv})
		self.issue_stock()
		return {"invoice": inv, "amount": amount, "currency": cur}

	@frappe.whitelist()
	def cancel_order(self):
		self._need_open()
		self.flags.internal = True
		self.db_set("status", "Cancelled")

	def issue_stock(self):
		"""Optional: take the sold stock items out of the outlet's warehouse."""
		wh = frappe.db.get_value("Outlet", self.outlet, "warehouse")
		if not wh:
			return
		items = []
		for row in self.items:
			it = frappe.db.get_value("Hotel Service Item", row.service_item, ["stock_item", "stock_qty"], as_dict=True)
			if it and it.stock_item:
				items.append({"item_code": it.stock_item, "qty": flt(row.qty) * flt(it.stock_qty or 1), "s_warehouse": wh})
		if not items:
			return
		se = frappe.new_doc("Stock Entry")
		se.update({"stock_entry_type": "Material Issue", "company": billing.settings().company, "posting_date": nowdate(), "remarks": _("Outlet order {0}").format(self.name)})
		for i in items:
			se.append("items", i)
		se.insert(ignore_permissions=True)
		se.submit()
