frappe.query_reports["Hotel Occupancy"] = {
	filters: [
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.get_today(), 29) },
		{ fieldname: "hotel", label: __("Hotel"), fieldtype: "Link", options: "Hotel" },
	],
};
