frappe.ui.form.on("Guest Folio", {
	refresh(frm) {
		if (frm.is_new()) return;
		const act = (method, args) =>
			frm.call({ doc: frm.doc, method, args, freeze: true }).then(() => frm.reload_doc());

		if (!["Closed", "To Bill", "Cancelled"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Add Charge"), () => {
				const d = new frappe.ui.Dialog({
					title: __("Add Charge"),
					fields: [
						{ fieldname: "service_item", fieldtype: "Link", options: "Hotel Service Item", label: __("Service"),
							onchange() {
								const v = d.get_value("service_item");
								if (v) frappe.db.get_value("Hotel Service Item", v, ["default_rate", "charge_type", "service_name"]).then((r) => {
									d.set_value("rate", r.message.default_rate);
									d.set_value("charge_type", r.message.charge_type === "Meal" ? "Meal" : "Service");
									d.set_value("description", r.message.service_name);
								});
							} },
						{ fieldname: "description", fieldtype: "Data", label: __("Description") },
						{ fieldname: "charge_type", fieldtype: "Select", label: __("Type"), options: "Meal\nService\nOther", default: "Service" },
						{ fieldname: "qty", fieldtype: "Float", label: __("Qty"), default: 1 },
						{ fieldname: "rate", fieldtype: "Currency", label: __("Price"), reqd: 1,
							description: __("In the service's own currency when a service is chosen, otherwise in {0}", [frm.doc.currency]) },
					],
					primary_action_label: __("Add"),
					primary_action(v) {
						d.hide();
						act("add_charge", v);
					},
				});
				d.show();
			});
		}

		const pay = (type, title) => () => {
			const d = new frappe.ui.Dialog({
				title,
				fields: [
					{ fieldname: "method", fieldtype: "Link", options: "Hotel Payment Method", label: __("Method"), reqd: 1,
						get_query: () => ({ filters: { enabled: 1 } }) },
					{ fieldname: "amount", fieldtype: "Float", label: __("Amount"), reqd: 1, description: __("In the currency of the chosen method") },
					{ fieldname: "exchange_rate", fieldtype: "Float", label: __("Rate to Billing Currency (optional)"), precision: 9,
						description: __("Leave empty to use today's rate from Currency Exchange") },
					{ fieldname: "reference", fieldtype: "Data", label: __("Reference") },
				],
				primary_action_label: __("Save"),
				primary_action(v) {
					d.hide();
					act("add_payment", Object.assign({ payment_type: type }, v));
				},
			});
			d.show();
		};
		if (frm.doc.status !== "Cancelled") {
			frm.add_custom_button(__("Receive Payment"), pay("Payment", __("Receive Payment")), __("Money"));
			frm.add_custom_button(__("Deposit"), pay("Deposit", __("Receive Deposit")), __("Money"));
			frm.add_custom_button(__("Refund"), pay("Refund", __("Refund")), __("Money"));
		}
		if (frm.doc.sales_invoice) {
			frm.add_custom_button(__("Open Invoice"), () => frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice));
		}
		if (frm.doc.reservation) {
			frm.add_custom_button(__("Open Reservation"), () => frappe.set_route("Form", "Reservation", frm.doc.reservation));
		}
		const cls = flt(frm.doc.balance) > 0.004 ? "orange" : "green";
		frm.dashboard.add_indicator(__("Balance: {0}", [format_currency(frm.doc.balance, frm.doc.currency)]), cls);
	},
});
