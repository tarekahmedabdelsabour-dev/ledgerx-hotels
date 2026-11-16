import frappe
from frappe import _
from frappe.utils import add_days, nowdate


def execute(filters=None):
	"""Charges posted to guest folios, by department and outlet, per currency (what the plan covers is shown at zero and left out)."""
	filters = filters or {}
	start = filters.get("from_date") or add_days(nowdate(), -29)
	end = filters.get("to_date") or nowdate()
	cond, args = "", [start, end]
	if filters.get("outlet"):
		cond = " and c.outlet = %s"
		args.append(filters["outlet"])
	rows = frappe.db.sql(
		f"""select c.department, ifnull(c.outlet, '') as outlet, f.currency, count(*) as lines, sum(c.amount) as net
		from `tabFolio Charge` c join `tabGuest Folio` f on f.name = c.parent
		where f.status != 'Cancelled' and c.included = 0 and c.charge_date between %s and %s {cond}
		group by c.department, c.outlet, f.currency order by c.department, net desc""", args, as_dict=True)
	cols = [
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 160},
		{"label": _("Outlet"), "fieldname": "outlet", "fieldtype": "Link", "options": "Outlet", "width": 160},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
		{"label": _("Lines"), "fieldname": "lines", "fieldtype": "Int", "width": 80},
		{"label": _("Revenue Before Taxes"), "fieldname": "net", "fieldtype": "Float", "width": 150},
	]
	return cols, rows
