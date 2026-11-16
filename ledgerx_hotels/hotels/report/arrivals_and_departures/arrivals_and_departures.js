frappe.query_reports["Arrivals and Departures"] = {
	filters: [
		{ fieldname: "date", label: __("Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "hotel", label: __("Hotel"), fieldtype: "Link", options: "Hotel" },
	],
};
