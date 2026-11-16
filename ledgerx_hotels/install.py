"""Install and migrate steps. Each step is idempotent and one failing step never aborts a migrate."""
import frappe

MODULE = "Hotels"
ROLES = ["Hotel Manager", "Hotel Front Desk", "Hotel Housekeeping", "Hotel Accountant"]
ROOM_ITEM = "Hotel Room Night"
SERVICE_ITEM = "Hotel Service"


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True
	return bool(set(frappe.get_roles()) & set(ROLES + ["System Manager"]))


def after_install():
	_all()


def after_migrate():
	_all()


def _all():
	for fn in (ensure_module, ensure_roles, ensure_items, ensure_settings):
		try:
			fn()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"ledgerx_hotels install step failed: {fn.__name__}")
	frappe.clear_cache()


def ensure_module():
	if not frappe.db.exists("Module Def", MODULE):
		frappe.get_doc({"doctype": "Module Def", "module_name": MODULE, "app_name": "ledgerx_hotels"}).insert(ignore_permissions=True)


def ensure_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


def ensure_items():
	group = "Services" if frappe.db.exists("Item Group", "Services") else "All Item Groups"
	uom = "Nos" if frappe.db.exists("UOM", "Nos") else frappe.db.get_value("UOM", {}, "name")
	for code in (ROOM_ITEM, SERVICE_ITEM):
		if not frappe.db.exists("Item", code):
			frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": code, "item_group": group, "stock_uom": uom,
				"is_stock_item": 0, "is_sales_item": 1, "is_purchase_item": 0, "include_item_in_manufacturing": 0}).insert(ignore_permissions=True)


def ensure_settings():
	s = frappe.get_doc("Hotel Settings")
	changed = False
	if not s.company:
		s.company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")
		changed = True
	if not s.room_item and frappe.db.exists("Item", ROOM_ITEM):
		s.room_item, changed = ROOM_ITEM, True
	if not s.service_item and frappe.db.exists("Item", SERVICE_ITEM):
		s.service_item, changed = SERVICE_ITEM, True
	if not s.selling_price_list:
		s.selling_price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
		changed = changed or bool(s.selling_price_list)
	if changed and s.company:
		s.save(ignore_permissions=True)
