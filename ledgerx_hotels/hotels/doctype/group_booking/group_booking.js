frappe.ui.form.on("Group Booking", {
	refresh(frm) {
		if (frm.is_new()) return;
		const act = (method, done) => frm.call({ doc: frm.doc, method, freeze: true }).then((r) => { frm.reload_doc(); if (done) done(r.message || {}); });
		if (frm.doc.status === "Draft") {
			frm.add_custom_button(__("Create Reservations"), () => act("create_reservations", (m) =>
				frappe.show_alert({ message: __("{0} reservations created", [m.reservations]), indicator: "green" }))).addClass("btn-primary");
		}
		if (frm.doc.status === "Rooms Created") {
			frm.add_custom_button(__("Confirm All Rooms"), () => act("confirm_all")).addClass("btn-primary");
		}
		if (["Rooms Created", "Confirmed"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Cancel Group"), () => frappe.confirm(__("Cancel every room of this group?"), () => act("cancel_group")));
		}
		frm.add_custom_button(__("Rooms of the Group"), () => frappe.set_route("List", "Reservation", { group: frm.doc.name }));
	},
});
