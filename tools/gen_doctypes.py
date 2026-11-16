"""Builds every DocType JSON of ledgerx_hotels from the compact table below.
Run from the repo root:  python3 tools/gen_doctypes.py   (rewrites ledgerx_hotels/hotels/doctype/*)"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..", "ledgerx_hotels", "hotels", "doctype")
TS = "2026-11-16 08:00:00.000000"
MODULE = "Hotels"

MGR, FD, HK, ACC = "Hotel Manager", "Hotel Front Desk", "Hotel Housekeeping", "Hotel Accountant"


def f(name, ftype, label=None, **kw):
	d = {"fieldname": name, "fieldtype": ftype}
	if ftype not in ("Section Break", "Column Break", "Tab Break"):
		d["label"] = label or name.replace("_", " ").title()
	elif label:
		d["label"] = label
	d.update(kw)
	return d


def sec(name, label=None, **kw):
	return f(name, "Section Break", label, **kw)


def col(name):
	return f(name, "Column Break")


def perms(*rows):
	out = []
	for role, mode in rows:
		p = {"role": role, "read": 1, "report": 1, "print": 1, "export": 1}
		if mode in ("rw", "rwc", "all"):
			p["write"] = 1
		if mode in ("rwc", "all"):
			p["create"] = 1
		if mode == "all":
			p["delete"] = 1
		out.append(p)
	out.append({"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "print": 1, "export": 1})
	return out


DT = {}


def doctype(name, fields, **kw):
	DT[name] = {"name": name, "fields": fields, **kw}


CUR = {"options": "currency"}

# ---------------------------------------------------------------- settings and masters
doctype("Hotel Settings", [
	f("company", "Link", "Company", options="Company", reqd=1),
	f("base_currency", "Link", "Company Currency", options="Currency", fetch_from="company.default_currency", read_only=1),
	f("cost_center", "Link", "Cost Center", options="Cost Center"),
	f("selling_price_list", "Link", "Price List", options="Price List", description="Only used to satisfy the invoice; the hotel sets every price itself."),
	col("cb1"),
	f("check_in_time", "Time", "Standard Check-in Time", default="14:00:00"),
	f("check_out_time", "Time", "Standard Check-out Time", default="12:00:00"),
	f("deposit_pct", "Percent", "Deposit Required (%)", default=0, description="Share of the stay total asked as a deposit when a reservation is confirmed."),
	sec("sb_tax", "Taxes and Service Charge"),
	f("service_rate", "Percent", "Service Charge (%)", default=12),
	f("vat_rate", "Percent", "VAT (%)", default=14),
	f("fee_rate", "Percent", "Tourism Fee (%)", default=0),
	f("vat_on_service", "Check", "VAT Also Applies to the Service Charge", default=1),
	col("cb2"),
	f("service_account", "Link", "Service Charge Account", options="Account"),
	f("vat_account", "Link", "VAT Account", options="Account"),
	f("fee_account", "Link", "Tourism Fee Account", options="Account"),
	sec("sb_items", "Revenue"),
	f("room_item", "Link", "Room Night Item", options="Item", description="Created automatically on install."),
	f("service_item", "Link", "Services Item", options="Item", description="Created automatically on install."),
	col("cb3"),
	f("room_income_account", "Link", "Room Revenue Account", options="Account"),
	f("service_income_account", "Link", "Services Revenue Account", options="Account"),
	sec("sb_cancel", "Cancellation Policy"),
	f("free_cancel_days", "Int", "Free Cancellation Until (days before arrival)", default=3),
	f("cancel_fee_pct", "Percent", "Late Cancellation Fee (% of the first night)", default=100),
	col("cb4"),
	f("corporate_billing_day", "Int", "Corporate Invoice Day of Month", default=1, description="On this day the company invoices for last month's stays are created."),
	sec("sb_dept", "Departments"),
	f("enable_fb", "Check", "Restaurants and Bars", default=1, description="Outlets and orders posted to the room."),
	f("enable_activities", "Check", "Activities and Services", default=1, description="Pool, beach, spa, trips: sessions with a limited capacity."),
	f("enable_groups", "Check", "Group Bookings", default=1),
	f("enable_operations", "Check", "Housekeeping and Maintenance", default=1),
	col("cb5"),
	f("fb_income_account", "Link", "Food and Beverage Revenue Account", options="Account"),
	f("activities_income_account", "Link", "Activities Revenue Account", options="Account"),
	f("walkin_customer", "Link", "Customer for Walk-in Sales", options="Customer", description="Used when a restaurant or an activity is paid on the spot by someone who is not staying."),
], issingle=1, icon="fa fa-cog", perms=perms((MGR, "rw"), (ACC, "r")))

doctype("Hotel Payment Method", [
	f("method_name", "Data", "Method", reqd=1, unique=1, in_list_view=1, description="For example: Cash EGP, Cash USD, Card EUR"),
	f("currency", "Link", "Currency", options="Currency", reqd=1, in_list_view=1),
	f("account", "Link", "Account", options="Account", reqd=1, in_list_view=1, description="The cash or bank account (in this currency) that receives the money."),
	f("mode_of_payment", "Link", "Mode of Payment", options="Mode of Payment"),
	f("enabled", "Check", "Enabled", default=1),
], autoname="field:method_name", title_field="method_name", icon="fa fa-money", perms=perms((MGR, "all"), (ACC, "r"), (FD, "r")))

doctype("Hotel", [
	f("hotel_name", "Data", "Hotel Name", reqd=1, unique=1, in_list_view=1),
	f("company", "Link", "Company", options="Company"),
	f("stars", "Select", "Stars", options="\n1\n2\n3\n4\n5"),
	col("cb1"),
	f("city", "Data", "City", in_list_view=1),
	f("phone", "Data", "Phone"),
	f("email", "Data", "Email", options="Email"),
	f("address", "Small Text", "Address"),
], autoname="field:hotel_name", title_field="hotel_name", icon="fa fa-building", perms=perms((MGR, "all"), (FD, "r"), (HK, "r"), (ACC, "r")))

doctype("Room Type", [
	f("room_type_name", "Data", "Room Type", reqd=1, in_list_view=1),
	f("hotel", "Link", "Hotel", options="Hotel", reqd=1, in_list_view=1, in_standard_filter=1),
	f("max_adults", "Int", "Max Adults", default=2),
	f("max_children", "Int", "Max Children", default=1),
	col("cb1"),
	f("beds", "Data", "Beds"),
	f("description", "Small Text", "Description"),
], autoname="format:RT-{#####}", title_field="room_type_name", show_title_field_in_link=1, icon="fa fa-bed",
	perms=perms((MGR, "all"), (FD, "r"), (HK, "r"), (ACC, "r")))

doctype("Hotel Room", [
	f("room_number", "Data", "Room Number", reqd=1, in_list_view=1),
	f("hotel", "Link", "Hotel", options="Hotel", reqd=1, in_list_view=1, in_standard_filter=1),
	f("room_type", "Link", "Room Type", options="Room Type", reqd=1, in_list_view=1, in_standard_filter=1),
	f("floor", "Data", "Floor"),
	col("cb1"),
	f("status", "Select", "Status", options="Clean\nDirty\nMaintenance\nOut of Order", default="Clean", in_list_view=1, in_standard_filter=1),
	f("notes", "Small Text", "Notes"),
], autoname="format:RM-{#####}", title_field="room_number", show_title_field_in_link=1, icon="fa fa-key",
	perms=perms((MGR, "all"), (FD, "rw"), (HK, "rw"), (ACC, "r")))

doctype("Hotel Service Item", [
	f("service_name", "Data", "Service", reqd=1, unique=1, in_list_view=1),
	f("charge_type", "Select", "Type", options="Meal\nService\nLaundry\nMinibar\nTransport\nOther", default="Service", in_list_view=1),
	f("currency", "Link", "Currency", options="Currency", reqd=1, in_list_view=1),
	f("default_rate", "Currency", "Default Price", options="currency", in_list_view=1),
	f("taxable", "Check", "Subject to Service Charge and Taxes", default=1),
	col("cb1"),
	f("outlet", "Link", "Outlet", options="Outlet", in_list_view=1, in_standard_filter=1),
	f("meal_period", "Select", "Meal Period", options="Any\nBreakfast\nLunch\nDinner\nSnack\nDrink", default="Any",
		description="The meal plans that already include this period give it free to the guest."),
	f("stock_item", "Link", "Stock Item", options="Item", description="Optional: issued from the outlet's warehouse when sold."),
	f("stock_qty", "Float", "Stock Quantity per Unit", default=1, depends_on="stock_item"),
], autoname="field:service_name", title_field="service_name", icon="fa fa-concierge-bell", perms=perms((MGR, "all"), (FD, "r"), (ACC, "r")))

doctype("Rate Plan", [
	f("plan_name", "Data", "Plan Name", reqd=1, in_list_view=1),
	f("hotel", "Link", "Hotel", options="Hotel", reqd=1, in_list_view=1, in_standard_filter=1),
	f("room_type", "Link", "Room Type", options="Room Type", reqd=1, in_list_view=1, in_standard_filter=1),
	f("enabled", "Check", "Enabled", default=1),
	col("cb1"),
	f("valid_from", "Date", "Valid From", reqd=1, in_list_view=1),
	f("valid_to", "Date", "Valid To", reqd=1, in_list_view=1),
	f("currency", "Link", "Currency", options="Currency", reqd=1, in_list_view=1),
	sec("sb_who", "Who It Is For"),
	f("applicable_to", "Select", "Applicable To", options="Public\nCorporate\nAgent", default="Public"),
	f("party", "Link", "Specific Company or Agent", options="Customer", depends_on="eval:doc.applicable_to!='Public'", description="Leave empty for every company or agent."),
	col("cb2"),
	f("priority", "Int", "Priority", default=0, description="When two plans fit the same night, the higher number wins."),
	f("min_nights", "Int", "Minimum Nights", default=0),
	sec("sb_rates", "Nightly Rates"),
	f("rate_room_only", "Currency", "Room Only", options="currency"),
	f("rate_bb", "Currency", "Bed & Breakfast", options="currency"),
	col("cb3"),
	f("rate_hb", "Currency", "Half Board", options="currency"),
	f("rate_fb", "Currency", "Full Board", options="currency"),
	f("rate_ai", "Currency", "All Inclusive", options="currency"),
	sec("sb_wk", "Weekends"),
	f("weekend_uplift_pct", "Percent", "Weekend Increase (%)", default=0),
	f("weekend_days", "Data", "Weekend Nights", default="3,4", description="Weekday numbers, Monday = 0. Default 3,4 = Thursday and Friday nights."),
], autoname="format:RP-{#####}", title_field="plan_name", show_title_field_in_link=1, icon="fa fa-tags",
	perms=perms((MGR, "all"), (FD, "r"), (ACC, "r")))

doctype("Hotel Promotion", [
	f("code", "Data", "Code", reqd=1, unique=1, in_list_view=1),
	f("enabled", "Check", "Enabled", default=1, in_list_view=1),
	f("description", "Small Text", "Description"),
	col("cb1"),
	f("discount_type", "Select", "Discount Type", options="Percent\nAmount", default="Percent", reqd=1),
	f("discount_value", "Float", "Discount Value", reqd=1, in_list_view=1, description="A percentage, or an amount in the reservation currency."),
	sec("sb_rules", "Conditions"),
	f("valid_from", "Date", "Valid From (check-in)", in_list_view=1),
	f("valid_to", "Date", "Valid To (check-in)", in_list_view=1),
	f("min_nights", "Int", "Minimum Nights", default=0),
	col("cb2"),
	f("room_type", "Link", "Only for Room Type", options="Room Type"),
	f("max_uses", "Int", "Maximum Uses", default=0, description="0 = unlimited."),
	f("used", "Int", "Times Used", read_only=1, default=0, no_copy=1),
], autoname="field:code", title_field="code", icon="fa fa-percent", perms=perms((MGR, "all"), (FD, "r"), (ACC, "r")))

# ---------------------------------------------------------------- reservation
doctype("Reservation Night", [
	f("night_date", "Date", "Night", in_list_view=1, read_only=1),
	f("rate_plan", "Link", "Rate Plan", options="Rate Plan", in_list_view=1, read_only=1),
	f("plan_currency", "Link", "Plan Currency", options="Currency", read_only=1),
	f("rate", "Currency", "Plan Rate", options="plan_currency", read_only=1),
	f("rate_in_folio_currency", "Currency", "Rate in Billing Currency", read_only=1, in_list_view=1, options="currency"),
], istable=1)

doctype("Reservation", [
	f("guest", "Link", "Guest", options="Customer", reqd=1, in_list_view=1, in_standard_filter=1),
	f("guest_name", "Data", "Name on the Room", in_list_view=1, description="Who really sleeps in the room (for groups and companies)."),
	f("hotel", "Link", "Hotel", options="Hotel", reqd=1, in_standard_filter=1),
	f("check_in", "Date", "Check-in", reqd=1, in_list_view=1, in_standard_filter=1),
	f("check_out", "Date", "Check-out", reqd=1, in_list_view=1),
	f("nights", "Int", "Nights", read_only=1),
	col("cb1"),
	f("status", "Select", "Status", options="Draft\nConfirmed\nChecked In\nChecked Out\nCancelled\nNo Show", default="Draft", read_only=1, in_list_view=1, in_standard_filter=1, no_copy=1),
	f("source", "Select", "Source", options="Direct\nAgent\nCorporate", default="Direct"),
	f("source_party", "Link", "Company or Agent", options="Customer", depends_on="eval:doc.source!='Direct'"),
	f("bill_to", "Select", "Bill To", options="Guest\nCompany or Agent", default="Guest", depends_on="eval:doc.source!='Direct'",
		description="'Company or Agent' keeps the folio open for the monthly invoice instead of invoicing at check-out."),
	sec("sb_room", "Room and Plan"),
	f("room_type", "Link", "Room Type", options="Room Type", reqd=1, in_list_view=1),
	f("room", "Link", "Room", options="Hotel Room", description="Left empty, a free room of the type is assigned when you confirm."),
	f("meal_plan", "Select", "Meal Plan", options="Room Only\nBed & Breakfast\nHalf Board\nFull Board\nAll Inclusive", default="Bed & Breakfast", reqd=1),
	col("cb2"),
	f("adults", "Int", "Adults", default=1),
	f("children", "Int", "Children", default=0),
	f("special_requests", "Small Text", "Special Requests"),
	sec("sb_price", "Price"),
	f("currency", "Link", "Billing Currency", options="Currency", reqd=1, description="The currency of the guest's bill. The guest can still pay in any accepted currency."),
	f("promotion", "Link", "Promotion Code", options="Hotel Promotion"),
	f("nightly_rates", "Table", "Nights", options="Reservation Night", read_only=1),
	col("cb3"),
	f("subtotal", "Currency", "Room Total", read_only=1, options="currency"),
	f("discount", "Currency", "Discount", read_only=1, options="currency"),
	f("total", "Currency", "Total After Discount (before taxes)", read_only=1, options="currency"),
	f("deposit_required", "Currency", "Deposit Required", read_only=1, options="currency"),
	sec("sb_link", "Transfer and Folio"),
	f("arrival_transfer", "Check", "Airport Pick-up"),
	f("flight_no", "Data", "Flight Number", depends_on="arrival_transfer"),
	f("transfer_vehicle", "Link", "Vehicle", options="Vehicle", depends_on="arrival_transfer"),
	col("cb4"),
	f("folio", "Link", "Guest Folio", options="Guest Folio", read_only=1, no_copy=1),
	f("group", "Link", "Group Booking", options="Group Booking", read_only=1, no_copy=1),
	f("promotion_counted", "Check", "Promotion Counted", hidden=1, read_only=1, no_copy=1),
], autoname="RSV-.YYYY.-.#####", title_field="guest", search_fields="guest,room,check_in", icon="fa fa-calendar-check-o", track_changes=1,
	is_calendar_and_gantt=0, perms=perms((MGR, "all"), (FD, "rwc"), (ACC, "r"), (HK, "r")))

doctype("Room Night Lock", [
	f("lock_key", "Data", "Key", reqd=1, unique=1, read_only=1),
	f("room", "Link", "Room", options="Hotel Room", reqd=1, read_only=1, in_list_view=1, in_standard_filter=1),
	f("night_date", "Date", "Night", reqd=1, read_only=1, in_list_view=1, in_standard_filter=1),
	f("reservation", "Link", "Reservation", options="Reservation", reqd=1, read_only=1, in_list_view=1),
], autoname="field:lock_key", icon="fa fa-lock", perms=perms((MGR, "r"), (FD, "r"), (ACC, "r")))

# ---------------------------------------------------------------- folio
doctype("Folio Charge", [
	f("charge_date", "Date", "Date", reqd=1, in_list_view=1),
	f("charge_type", "Select", "Type", options="Room\nMeal\nService\nActivity\nCancellation\nOther", default="Service", in_list_view=1),
	f("department", "Select", "Department", options="Rooms\nFood and Beverage\nActivities\nOther", default="Other"),
	f("outlet", "Link", "Outlet", options="Outlet"),
	f("description", "Data", "Description", in_list_view=1),
	f("included", "Check", "Included in the Plan"),
	f("meal_period", "Select", "Meal Period", options="\nBreakfast\nLunch\nDinner\nSnack\nDrink", hidden=1),
	f("source_ref", "Data", "Source", read_only=1),
	f("service_item", "Link", "Service", options="Hotel Service Item"),
	f("qty", "Float", "Qty", default=1, in_list_view=1),
	f("rate", "Currency", "Rate", in_list_view=1, options="currency"),
	f("amount", "Currency", "Amount", read_only=1, in_list_view=1, options="currency"),
	f("taxable", "Check", "Taxable", default=1),
], istable=1)

doctype("Folio Payment", [
	f("payment_date", "Date", "Date", reqd=1, in_list_view=1),
	f("payment_type", "Select", "Type", options="Deposit\nPayment\nRefund", default="Payment", reqd=1, in_list_view=1),
	f("method", "Link", "Method", options="Hotel Payment Method", reqd=1, in_list_view=1),
	f("pay_currency", "Link", "Currency", options="Currency", fetch_from="method.currency", read_only=1),
	f("amount", "Currency", "Amount", options="pay_currency", reqd=1, in_list_view=1),
	f("exchange_rate", "Float", "Rate to Billing Currency", precision="9", read_only=1),
	f("amount_in_folio_currency", "Currency", "Amount in Billing Currency", read_only=1, in_list_view=1, options="currency"),
	f("reference", "Data", "Reference"),
	f("payment_entry", "Link", "Payment Entry", options="Payment Entry", read_only=1),
], istable=1)

doctype("Guest Folio", [
	f("reservation", "Link", "Reservation", options="Reservation", reqd=1, in_list_view=1, in_standard_filter=1),
	f("guest", "Link", "Guest", options="Customer", read_only=1, in_list_view=1),
	f("bill_to_customer", "Link", "Billed To", options="Customer", read_only=1),
	f("company", "Link", "Company", options="Company", read_only=1),
	col("cb1"),
	f("status", "Select", "Status", options="Open\nTo Bill\nClosed\nCancelled", default="Open", read_only=1, in_list_view=1, in_standard_filter=1),
	f("currency", "Link", "Billing Currency", options="Currency", read_only=1),
	f("room", "Link", "Room", options="Hotel Room", read_only=1),
	sec("sb_charges", "Charges"),
	f("charges", "Table", "Charges", options="Folio Charge"),
	sec("sb_pay", "Payments"),
	f("payments", "Table", "Payments", options="Folio Payment", read_only=1, description="Add money from the buttons on top (Receive Payment, Deposit, Refund), so a Payment Entry is made for every line."),
	sec("sb_tot", "Totals"),
	f("net_total", "Currency", "Charges Before Taxes", read_only=1, options="currency"),
	f("service_charge", "Currency", "Service Charge", read_only=1, options="currency"),
	f("vat", "Currency", "VAT", read_only=1, options="currency"),
	f("tourism_fee", "Currency", "Tourism Fee", read_only=1, options="currency"),
	col("cb2"),
	f("grand_total", "Currency", "Total", read_only=1, options="currency", in_list_view=1),
	f("paid", "Currency", "Paid", read_only=1, options="currency", in_list_view=1),
	f("balance", "Currency", "Balance", read_only=1, options="currency", in_list_view=1),
	sec("sb_inv", "Invoice"),
	f("sales_invoice", "Link", "Sales Invoice", options="Sales Invoice", read_only=1, no_copy=1),
	f("room_charges_posted", "Check", "Room Charges Posted", read_only=1, hidden=1, no_copy=1),
], autoname="FOL-.YYYY.-.#####", title_field="guest", icon="fa fa-file-text-o", track_changes=1,
	perms=perms((MGR, "all"), (FD, "rw"), (ACC, "rw")))

# ---------------------------------------------------------------- food and beverage
doctype("Outlet", [
	f("outlet_name", "Data", "Outlet", reqd=1, unique=1, in_list_view=1),
	f("hotel", "Link", "Hotel", options="Hotel", reqd=1, in_list_view=1, in_standard_filter=1),
	f("outlet_type", "Select", "Type", options="Restaurant\\nCafe\\nBar\\nPool Bar\\nBeach\\nSpa\\nShop\\nOther", default="Restaurant", in_list_view=1),
	f("enabled", "Check", "Enabled", default=1),
	col("cb1"),
	f("included_in_meal_plans", "Check", "Meal Plans Are Served Here", default=1,
		description="Untick for a paid à la carte restaurant: guests on half board or all inclusive pay there."),
	f("income_account", "Link", "Revenue Account", options="Account", description="Empty: the department account in Hotel Settings."),
	f("cost_center", "Link", "Cost Center", options="Cost Center"),
	f("warehouse", "Link", "Warehouse", options="Warehouse", description="Where stock items sold here are issued from."),
], autoname="field:outlet_name", title_field="outlet_name", icon="fa fa-cutlery", perms=perms((MGR, "all"), (FD, "rw"), (ACC, "r")))

doctype("Outlet Order Item", [
	f("service_item", "Link", "Item", options="Hotel Service Item", reqd=1, in_list_view=1),
	f("qty", "Float", "Qty", default=1, reqd=1, in_list_view=1),
	f("rate", "Currency", "Price", in_list_view=1, options="currency", read_only=1),
	f("amount", "Currency", "Amount", in_list_view=1, options="currency", read_only=1),
	f("included_qty", "Float", "Covered by the Plan", read_only=1),
	f("meal_period", "Data", "Meal Period", read_only=1, hidden=1),
], istable=1)

doctype("Outlet Order", [
	f("outlet", "Link", "Outlet", options="Outlet", reqd=1, in_list_view=1, in_standard_filter=1),
	f("order_time", "Datetime", "Time", reqd=1, default="Now"),
	f("table_no", "Data", "Table"),
	col("cb1"),
	f("status", "Select", "Status", options="Open\\nPosted to Room\\nPaid\\nCancelled", default="Open", read_only=1, in_list_view=1, in_standard_filter=1, no_copy=1),
	f("currency", "Link", "Currency", options="Currency", reqd=1, description="The currency of the bill (the room's, or the one the customer pays in)."),
	sec("sb_who", "Who Pays"),
	f("reservation", "Link", "Room (Checked-in Reservation)", options="Reservation", description="Leave empty for someone who is not staying: they pay on the spot."),
	f("guest_name", "Data", "Guest", read_only=1),
	f("persons", "Int", "Persons at the Table", default=1, description="Used for meals the plan already includes."),
	sec("sb_items", "Order"),
	f("items", "Table", "Items", options="Outlet Order Item", reqd=1),
	col("cb2"),
	f("net_total", "Currency", "Total", read_only=1, options="currency"),
	f("sales_invoice", "Link", "Sales Invoice", options="Sales Invoice", read_only=1, no_copy=1),
	f("folio", "Link", "Guest Folio", options="Guest Folio", read_only=1, no_copy=1),
], autoname="ORD-.YYYY.-.#####", title_field="outlet", icon="fa fa-shopping-basket", track_changes=1,
	perms=perms((MGR, "all"), (FD, "rwc"), (ACC, "r")))

# ---------------------------------------------------------------- activities
doctype("Hotel Activity", [
	f("activity_name", "Data", "Activity", reqd=1, unique=1, in_list_view=1),
	f("outlet", "Link", "Outlet", options="Outlet", in_standard_filter=1, description="The spa, beach or pool that runs it (for the revenue account and cost center)."),
	f("category", "Select", "Category", options="Pool\\nBeach\\nWater Sports\\nSpa\\nSports\\nTrip\\nEntertainment\\nKids\\nOther", default="Other", in_list_view=1),
	col("cb1"),
	f("currency", "Link", "Currency", options="Currency", reqd=1),
	f("price", "Currency", "Price per Person", options="currency", in_list_view=1),
	f("capacity", "Int", "Default Capacity", default=10),
	f("duration_minutes", "Int", "Duration (minutes)", default=60),
	f("included_in_all_inclusive", "Check", "Free for All Inclusive Guests"),
	f("taxable", "Check", "Subject to Service Charge and Taxes", default=1),
], autoname="field:activity_name", title_field="activity_name", icon="fa fa-life-ring", perms=perms((MGR, "all"), (FD, "r"), (ACC, "r")))

doctype("Activity Session", [
	f("activity", "Link", "Activity", options="Hotel Activity", reqd=1, in_list_view=1, in_standard_filter=1),
	f("session_date", "Date", "Date", reqd=1, in_list_view=1, in_standard_filter=1),
	f("start_time", "Time", "Start", reqd=1, in_list_view=1),
	col("cb1"),
	f("capacity", "Int", "Capacity", reqd=1, in_list_view=1),
	f("booked", "Int", "Booked", read_only=1, default=0, in_list_view=1),
	f("status", "Select", "Status", options="Open\\nClosed\\nCancelled", default="Open", in_standard_filter=1),
], autoname="format:SES-{#####}", icon="fa fa-clock-o", perms=perms((MGR, "all"), (FD, "rw")))

doctype("Activity Booking", [
	f("session", "Link", "Session", options="Activity Session", reqd=1, in_list_view=1, in_standard_filter=1),
	f("activity", "Link", "Activity", options="Hotel Activity", fetch_from="session.activity", read_only=1, in_list_view=1),
	f("session_date", "Date", "Date", fetch_from="session.session_date", read_only=1, in_list_view=1),
	col("cb1"),
	f("status", "Select", "Status", options="Booked\\nCancelled", default="Booked", read_only=1, in_list_view=1, no_copy=1),
	f("persons", "Int", "Persons", default=1, reqd=1),
	f("currency", "Link", "Currency", options="Currency", reqd=1),
	sec("sb_who", "Who Pays"),
	f("reservation", "Link", "Room (Checked-in Reservation)", options="Reservation", description="Leave empty for someone who is not staying: they pay on the spot."),
	f("guest_name", "Data", "Guest"),
	col("cb2"),
	f("total", "Currency", "Total", read_only=1, options="currency"),
	f("included", "Check", "Included in the Plan", read_only=1),
	f("sales_invoice", "Link", "Sales Invoice", options="Sales Invoice", read_only=1, no_copy=1),
	f("folio", "Link", "Guest Folio", options="Guest Folio", read_only=1, no_copy=1),
], autoname="ACT-.YYYY.-.#####", title_field="activity", icon="fa fa-ticket", track_changes=1,
	perms=perms((MGR, "all"), (FD, "rwc"), (ACC, "r")))

# ---------------------------------------------------------------- groups
doctype("Group Booking Line", [
	f("room_type", "Link", "Room Type", options="Room Type", reqd=1, in_list_view=1),
	f("rooms", "Int", "Rooms", default=1, reqd=1, in_list_view=1),
	f("adults", "Int", "Adults per Room", default=2, in_list_view=1),
	f("children", "Int", "Children per Room", default=0),
], istable=1)

doctype("Group Booking", [
	f("group_name", "Data", "Group", reqd=1, in_list_view=1),
	f("customer", "Link", "Company or Agent", options="Customer", reqd=1, in_list_view=1, in_standard_filter=1),
	f("hotel", "Link", "Hotel", options="Hotel", reqd=1),
	f("status", "Select", "Status", options="Draft\\nRooms Created\\nConfirmed\\nCancelled", default="Draft", read_only=1, in_list_view=1, no_copy=1),
	col("cb1"),
	f("check_in", "Date", "Check-in", reqd=1, in_list_view=1),
	f("check_out", "Date", "Check-out", reqd=1),
	f("meal_plan", "Select", "Meal Plan", options="Room Only\\nBed & Breakfast\\nHalf Board\\nFull Board\\nAll Inclusive", default="Bed & Breakfast", reqd=1),
	f("currency", "Link", "Billing Currency", options="Currency", reqd=1),
	f("source", "Select", "Source", options="Corporate\\nAgent", default="Agent"),
	sec("sb_lines", "Rooms Needed"),
	f("lines", "Table", "Rooms", options="Group Booking Line", reqd=1),
	f("notes", "Small Text", "Notes"),
	sec("sb_res", "Reservations"),
	f("total_rooms", "Int", "Total Rooms", read_only=1),
], autoname="GRP-.YYYY.-.####", title_field="group_name", icon="fa fa-users", track_changes=1,
	perms=perms((MGR, "all"), (FD, "rwc"), (ACC, "r")))

# ---------------------------------------------------------------- housekeeping and maintenance
doctype("Housekeeping Task", [
	f("room", "Link", "Room", options="Hotel Room", reqd=1, in_list_view=1, in_standard_filter=1),
	f("task_type", "Select", "Task", options="Cleaning After Departure\\nDaily Cleaning\\nTurndown\\nInspection\\nDeep Clean", default="Cleaning After Departure", in_list_view=1),
	f("task_date", "Date", "Date", default="Today", reqd=1, in_list_view=1, in_standard_filter=1),
	col("cb1"),
	f("status", "Select", "Status", options="Open\\nDone", default="Open", in_list_view=1, in_standard_filter=1),
	f("assigned_to", "Link", "Assigned To", options="Employee"),
	f("notes", "Small Text", "Notes"),
], autoname="format:HK-{#####}", icon="fa fa-trash", perms=perms((MGR, "all"), (HK, "rwc"), (FD, "rw")))

doctype("Maintenance Request", [
	f("room", "Link", "Room", options="Hotel Room", in_list_view=1, in_standard_filter=1),
	f("area", "Data", "Area (when it is not a room)", in_list_view=1),
	f("issue", "Small Text", "Problem", reqd=1),
	col("cb1"),
	f("priority", "Select", "Priority", options="Low\\nNormal\\nHigh\\nUrgent", default="Normal", in_list_view=1, in_standard_filter=1),
	f("status", "Select", "Status", options="Open\\nIn Progress\\nDone", default="Open", in_list_view=1, in_standard_filter=1),
	f("block_room", "Check", "Take the Room Out of Service Until Done"),
	f("assigned_to", "Link", "Assigned To", options="Employee"),
	f("resolution", "Small Text", "What Was Done"),
], autoname="format:MNT-{#####}", icon="fa fa-wrench", perms=perms((MGR, "all"), (HK, "rwc"), (FD, "rwc")))

doctype("Guest Request", [
	f("reservation", "Link", "Reservation", options="Reservation", in_list_view=1),
	f("room", "Link", "Room", options="Hotel Room", fetch_from="reservation.room", read_only=1),
	f("request_type", "Select", "Type", options="Request\\nComplaint\\nLost and Found\\nCompliment", default="Request", in_list_view=1, in_standard_filter=1),
	f("details", "Small Text", "Details", reqd=1),
	col("cb1"),
	f("status", "Select", "Status", options="Open\\nIn Progress\\nClosed", default="Open", in_list_view=1, in_standard_filter=1),
	f("assigned_to", "Link", "Assigned To", options="Employee"),
	f("outcome", "Small Text", "Outcome"),
], autoname="format:GR-{#####}", icon="fa fa-comments", perms=perms((MGR, "all"), (FD, "rwc"), (HK, "rw")))


def build():
	os.makedirs(ROOT, exist_ok=True)
	for name, d in DT.items():
		fields = d["fields"]
		order = [x["fieldname"] for x in fields]
		istable = d.get("istable", 0)
		out = {
			"actions": [], "creation": TS, "doctype": "DocType", "engine": "InnoDB", "field_order": order, "fields": fields,
			"links": [], "modified": TS, "modified_by": "Administrator", "module": MODULE, "name": name, "owner": "Administrator",
			"sort_field": "creation", "sort_order": "DESC", "states": [],
			"permissions": [] if istable else d.get("perms", []),
		}
		for k in ("autoname", "title_field", "icon", "track_changes", "issingle", "istable", "show_title_field_in_link", "search_fields"):
			if k in d:
				out[k] = d[k]
		if "autoname" not in d and not istable and not d.get("issingle"):
			out["autoname"] = "hash"
		out["allow_rename"] = 0
		slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
		folder = os.path.join(ROOT, slug)
		os.makedirs(folder, exist_ok=True)
		open(os.path.join(folder, "__init__.py"), "a").close()
		with open(os.path.join(folder, slug + ".json"), "w", encoding="utf-8") as fh:
			json.dump(out, fh, indent=1, ensure_ascii=False)
			fh.write("\n")
		py = os.path.join(folder, slug + ".py")
		if not os.path.exists(py):
			cls = "".join(w.capitalize() for w in re.split(r"[^A-Za-z0-9]+", name))
			with open(py, "w") as fh:
				fh.write(f"from frappe.model.document import Document\n\n\nclass {cls}(Document):\n\tpass\n")


if __name__ == "__main__":
	build()
	print(len(DT), "doctypes")
