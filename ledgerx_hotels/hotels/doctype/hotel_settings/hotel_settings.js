frappe.ui.form.on("Hotel Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Create Corporate Invoices Now"), () =>
			frappe.call({ method: "ledgerx_hotels.engine.billing.bill_corporate_now", freeze: true }).then((r) => {
				const n = (r.message || []).length;
				frappe.msgprint(n ? __("Created {0} invoice(s): {1}", [n, r.message.join(", ")]) : __("Nothing is waiting to be billed."));
			}));
	},
});
