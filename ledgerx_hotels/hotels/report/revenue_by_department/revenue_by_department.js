frappe.query_reports["Revenue by Department"] = {
	filters: [
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.get_today(), -29) },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "outlet", label: __("Outlet"), fieldtype: "Link", options: "Outlet" },
	],
};
