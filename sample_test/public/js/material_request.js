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


frappe.ui.form.on('Material Request Item', {
    item_code: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item_code) {
            frappe.call({
                method: 'sample_test.sample_test.override.material_request.get_suppliers_for_item',
                args: {
                    item_code: row.item_code
                },
                callback: function(response) {
                    if (response.message) {
                        const suppliers = response.message.join(', ');
                        frappe.model.set_value(cdt, cdn, 'custom_default_suppliers', suppliers);
                    }
                }
            });
        }
    }
});

frappe.ui.form.on('Material Request', {
    refresh: function(frm) {
        if (!frm.fields_dict.items) return;

        frm.fields_dict.items.grid.add_custom_button(__('Check Item Info'), function() {
            check_item_info(frm);
        });

        refresh_items_info(frm);
    },
});

function refresh_items_info(frm) {
    let promises = frm.doc.items.map(function(item) {
        return new Promise((resolve) => {
            frappe.call({
                method: 'sample_test.sample_test.override.material_request.get_suppliers_for_item',
                args: {
                    item_code: item.item_code
                },
                callback: function(response) {
                    if (response.message) {
                        const suppliers = response.message.join(', ');
                        frappe.model.set_value(item.doctype, item.name, 'custom_default_suppliers', suppliers);
                    }
                    resolve();
                }
            });
        });
    });

    return Promise.all(promises);
}

function check_item_info(frm) {
    refresh_items_info(frm).then(() => {
        let items_info = [];

        frm.doc.items.forEach(function(item, index) {
            items_info.push({
                index: index + 1,
                item_code: item.item_code,
                item_name: item.item_name,
                custom_default_suppliers: item.custom_default_suppliers || ''
            });
        });

        // Sort items by their original order (index)
        items_info.sort((a, b) => a.index - b.index);

        let message = `
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>${__('Sr')}</th>
                        <th>${__('Item Code')}</th>
                        <th>${__('Item Name')}</th>
                        <th>${__('Custom Default Suppliers')}</th>
                    </tr>
                </thead>
                <tbody>`;

        items_info.forEach(function(item) {
            let row_style = item.custom_default_suppliers ? '' : ' style="color: red;"';
            message += `
                <tr${row_style}>
                    <td>${item.index}</td>
                    <td>${item.item_code}</td>
                    <td>${item.item_name}</td>
                    <td>${item.custom_default_suppliers}</td>
                </tr>`;
        });

        message += `
                </tbody>
            </table>`;

        frappe.msgprint({
            title: __('Item Information'),
            indicator: 'blue',
            message: message
        });
    });
}




