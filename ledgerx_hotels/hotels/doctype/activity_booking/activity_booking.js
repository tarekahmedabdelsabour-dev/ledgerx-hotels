frappe.ui.form.on("Activity Booking", {
	setup(frm) {
		frm.set_query("reservation", () => ({ filters: { status: "Checked In" } }));
		frm.set_query("session", () => ({ filters: { status: "Open", session_date: [">=", frappe.datetime.get_today()] } }));
	},
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Booked") return;
		const act = (method, args, done) => frm.call({ doc: frm.doc, method, args: args || {}, freeze: true }).then((r) => { frm.reload_doc(); if (done) done(r.message || {}); });
		if (!frm.doc.reservation && !frm.doc.sales_invoice && frm.doc.total) {
			frm.add_custom_button(__("Pay Now"), () => {
				const d = new frappe.ui.Dialog({
					title: __("Pay Now"),
					fields: [{ fieldname: "method", fieldtype: "Link", options: "Hotel Payment Method", label: __("Method"), reqd: 1, get_query: () => ({ filters: { enabled: 1 } }) }],
					primary_action_label: __("Receive"),
					primary_action(v) { d.hide(); act("pay_now", v, (m) => m.invoice && frappe.msgprint(__("Received {0} {1}. Invoice {2}.", [m.amount, m.currency, m.invoice]))); },
				});
				d.show();
			}).addClass("btn-primary");
		}
		frm.add_custom_button(__("Cancel Booking"), () => frappe.confirm(__("Cancel this booking?"), () => act("cancel_booking")));
	},
});
