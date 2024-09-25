frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        // Adding the custom "Request for Raw Materials" button
        frm.add_custom_button(__('Request for Raw Materials '), function() {
            frappe.call({
                method: "erpnext.selling.doctype.sales_order.sales_order.get_work_order_items",
                args: {
                    sales_order: frm.docname,
                    for_raw_material_request: 1
                },
                callback: function(r) {
                    if (!r.message) {
                        frappe.msgprint({
                            message: __("No Items with Bill of Materials."),
                            indicator: "orange"
                        });
                        return;
                    } else {
                        // Create the dialog for Raw Material Request
                        let dialog = new frappe.ui.Dialog({
                            title: __("Items for Raw Material Request"),
                            fields: [
                                {fieldtype: "Check", fieldname: "include_exploded_items", label: __("Include Exploded Items")},
                                {fieldtype: "Check", fieldname: "ignore_existing_ordered_qty", label: __("Ignore Existing Ordered Qty")},
                                {
                                    fieldtype: "Table",
                                    fieldname: "items",
                                    description: __("Select BOM, Qty, and For Warehouse"),
                                    fields: [
                                        {fieldtype: "Read Only", fieldname: "item_code", label: __("Item Code"), in_list_view: 1},
                                        {fieldtype: "Link", fieldname: "warehouse", options: "Warehouse", label: __("For Warehouse"), in_list_view: 1},
                                        {fieldtype: "Link", fieldname: "bom", options: "BOM", reqd: 1, label: __("BOM"), in_list_view: 1},
                                        {fieldtype: "Float", fieldname: "required_qty", reqd: 1, label: __("Qty"), in_list_view: 1}
                                    ],
                                    data: r.message,
                                    get_data: function() {
                                        return r.message;
                                    }
                                }
                            ],
                            primary_action_label: __("Create"),
                            primary_action: function() {
                                let data = dialog.get_values();
                                if (data) {
                                    frappe.call({
                                        method: "erpnext.selling.doctype.sales_order.sales_order.make_raw_material_request",
                                        args: {
                                            items: data,
                                            company: frm.doc.company,
                                            sales_order: frm.docname
                                        },
                                        callback: function(r) {
                                            if (r.message) {
                                                frappe.msgprint(__("Material Request {0} submitted.", [
                                                    `<a href="/app/material-request/${r.message.name}">${r.message.name}</a>`
                                                ]));
                                            }
                                            dialog.hide();
                                            frm.reload_doc();
                                        }
                                    });
                                }
                            }
                        });

                        // Adding a "Custom Create" button in the dialog box
                        dialog.set_secondary_action(function() {
                            let data = dialog.get_values();
                            if (data) {
                                // Call your custom method for the "Custom Create" button
                                frappe.call({
                                    method: 'sample_test.sample_test.override.req_for_RM.make_raw_material_req',
                                    args: {
                                        items: data,
                                        company: frm.doc.company,
                                        sales_order: frm.docname
                                    },
                                    callback: function(r) {
                                        if (r.message) {
                                            frappe.msgprint(__("Custom Material Request {0} submitted.", [
                                                `<a href="/app/material-request/${r.message.name}">${r.message.name}</a>`
                                            ]));
                                        }
                                        dialog.hide();
                                        frm.reload_doc();
                                    }
                                });
                            }
                        });
                        dialog.set_secondary_action_label(__('Custom Create'));

                        // After the dialog is shown, change the style of the "Custom Create" button
                        dialog.show();
                        setTimeout(function() {
                            // Find the secondary button and style it
                            dialog.$wrapper.find('.modal-footer .btn-secondary').addClass('btn-primary');
                        }, 100);

                    }
                }
            });
        }, __('Create'));
    }
});
