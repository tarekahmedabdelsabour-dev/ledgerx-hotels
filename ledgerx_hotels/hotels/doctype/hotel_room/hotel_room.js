frappe.ui.form.on("Hotel Room", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.status !== "Clean") {
			frm.add_custom_button(__("Mark Clean"), () => frm.set_value("status", "Clean").then(() => frm.save()));
		}
		if (frm.doc.status === "Clean") {
			frm.add_custom_button(__("Mark Dirty"), () => frm.set_value("status", "Dirty").then(() => frm.save()));
		}
	},
});
