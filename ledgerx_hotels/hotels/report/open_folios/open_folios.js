frappe.query_reports["Open Folios"] = {
	filters: [{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nOpen\nTo Bill\nClosed" }],
};
