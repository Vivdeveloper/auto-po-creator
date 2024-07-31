frappe.ui.form.on('Material Request', {
    refresh: function(frm) {
        if (!frm.doc.__islocal && frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Auto Create PO'), function() {
                frappe.call({
                    method: 'sample_test.sample_test.override.material_request.create_purchase_orders',
                    args: {
                        material_request: frm.doc.name
                    },
                    callback: function(response) {
                        let message = '';
                        if (response.message.created.length > 0) {
                            message += '<b>' + __('Purchase Orders Created Successfully:') + '</b><br>';
                            response.message.created.forEach(po => {
                                message += `<a href='/app/purchase-order/${po.name}'>${po.name}</a> (Supplier: ${po.supplier})<br>`;
                            });
                        }
                        if (response.message.existing.length > 0) {
                            message += '<br><b>' + __('Existing Purchase Orders:') + '</b><br>';
                            response.message.existing.forEach(po => {
                                message += `A purchase order for supplier ${po.supplier} has already been created: <a href='/app/purchase-order/${po.po_name}'>${po.po_name}</a><br>`;
                            });
                        }
                        if (response.message.created.length === 0 && response.message.existing.length > 0) {
                            message = __('All purchase orders for the suppliers have already been created.');
                        }
                        frappe.msgprint({
                            title: __('Purchase Order Creation'),
                            indicator: 'green',
                            message: message
                        });
                    }
                });
            });
        }
    }
});