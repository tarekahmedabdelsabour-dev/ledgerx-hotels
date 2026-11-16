frappe.ui.form.on("Reservation", {
	setup(frm) {
		frm.set_query("room_type", () => ({ filters: { hotel: frm.doc.hotel } }));
		frm.set_query("room", () => ({ filters: { hotel: frm.doc.hotel, room_type: frm.doc.room_type } }));
	},

	refresh(frm) {
		if (frm.is_new()) return;
		const act = (method, args, done) =>
			frm.call({ doc: frm.doc, method, args: args || {}, freeze: true }).then((r) => {
				frm.reload_doc();
				if (done) done(r.message || {});
			});
		const s = frm.doc.status;

		if (s === "Draft") {
			frm.add_custom_button(__("Confirm"), () => act("confirm", {}, (m) => {
				frappe.show_alert({ message: __("Confirmed - room {0}", [m.room]), indicator: "green" });
			})).addClass("btn-primary");
		}
		if (s === "Confirmed") {
			frm.add_custom_button(__("Check In"), () => act("check_in_guest")).addClass("btn-primary");
			frm.add_custom_button(__("Change Dates"), () => frm.trigger("change_dates"), __("Change"));
			frm.add_custom_button(__("Change Room"), () => frm.trigger("change_room"), __("Change"));
			frm.add_custom_button(__("Cancel Reservation"), () => frappe.confirm(__("Cancel this reservation?"), () =>
				act("cancel_reservation", {}, (m) => {
					if (m.fee) frappe.msgprint(__("A late cancellation fee of {0} was added and invoiced.", [format_currency(m.fee, frm.doc.currency)]));
				})), __("Change"));
			frm.add_custom_button(__("No Show"), () => frappe.confirm(__("Mark the guest as a no-show? The first night is charged."), () =>
				act("mark_no_show")), __("Change"));
		}
		if (s === "Checked In") {
			frm.add_custom_button(__("Check Out"), () => act("check_out_guest", {}, (m) => {
				if (m.invoice) frappe.msgprint(__("Invoice {0} created.", [m.invoice]));
			})).addClass("btn-primary");
			frm.add_custom_button(__("Change Room"), () => frm.trigger("change_room"), __("Change"));
		}
		if (frm.doc.folio) {
			frm.add_custom_button(__("Open Folio"), () => frappe.set_route("Form", "Guest Folio", frm.doc.folio));
		}
		const ind = { Draft: "gray", Confirmed: "blue", "Checked In": "green", "Checked Out": "darkgrey", Cancelled: "red", "No Show": "orange" };
		frm.page.set_indicator(__(s), ind[s] || "gray");
	},

	change_room(frm) {
		frappe.call({
			method: "ledgerx_hotels.hotels.doctype.reservation.reservation.available_rooms",
			args: { hotel: frm.doc.hotel, room_type: frm.doc.room_type, check_in: frm.doc.check_in, check_out: frm.doc.check_out },
		}).then((r) => {
			const opts = (r.message || []).map((x) => ({ label: x.room_number, value: x.name }));
			if (!opts.length) return frappe.msgprint(__("No other free room of this type."));
			const d = new frappe.ui.Dialog({
				title: __("Change Room"),
				fields: [{ fieldname: "room", fieldtype: "Autocomplete", label: __("Room"), options: opts, reqd: 1 }],
				primary_action_label: __("Change"),
				primary_action(v) {
					d.hide();
					frm.call({ doc: frm.doc, method: "change_room", args: { room: v.room }, freeze: true }).then(() => frm.reload_doc());
				},
			});
			d.show();
		});
	},

	change_dates(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Change Dates"),
			fields: [
				{ fieldname: "check_in", fieldtype: "Date", label: __("Check-in"), reqd: 1, default: frm.doc.check_in },
				{ fieldname: "check_out", fieldtype: "Date", label: __("Check-out"), reqd: 1, default: frm.doc.check_out },
			],
			primary_action_label: __("Change"),
			primary_action(v) {
				d.hide();
				frm.call({ doc: frm.doc, method: "change_dates", args: v, freeze: true }).then(() => frm.reload_doc());
			},
		});
		d.show();
	},
});
