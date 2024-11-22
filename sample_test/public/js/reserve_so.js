// frappe.ui.form.on("Sales Order", {
//     refresh: function(frm) {
//         if (frm.doc.docstatus === 1) {
//             // Add the button without any condition
//             frm.add_custom_button(
//                 __("Test Reserve Packed Items"),
//                 () => frm.events.create_packed_stock_reservation_entries(frm)
//             );
//         }
//     },

//     // Create the method to reserve stock for packed items
//     create_packed_stock_reservation_entries: function(frm) {
//         const dialog = new frappe.ui.Dialog({
//             title: __("Reserve Stock for Packed Items"),
//             size: "extra-large",
//             fields: [
//                 {
//                     fieldname: "set_warehouse",
//                     fieldtype: "Link",
//                     label: __("Set Warehouse"),
//                     options: "Warehouse",
//                     default: frm.doc.set_warehouse,
//                     get_query: () => {
//                         return {
//                             filters: [["Warehouse", "is_group", "!=", 1]],
//                         };
//                     },
//                     onchange: () => {
//                         if (dialog.get_value("set_warehouse")) {
//                             dialog.fields_dict.packed_items.df.data.forEach((row) => {
//                                 row.warehouse = dialog.get_value("set_warehouse");
//                             });
//                             dialog.fields_dict.packed_items.grid.refresh();
//                         }
//                     },
//                 },
//                 { fieldtype: "Section Break" },
//                 {
//                     fieldname: "packed_items",
//                     fieldtype: "Table",
//                     label: __("Packed Items to Reserve"),
//                     allow_bulk_edit: false,
//                     cannot_add_rows: true,
//                     cannot_delete_rows: true,
//                     data: [],
//                     fields: [
//                         {
//                             fieldname: "packed_item",
//                             fieldtype: "Link",
//                             label: __("Packed Item"),
//                             options: "Packed Item",
//                             reqd: 1,
//                             in_list_view: 1,
//                         },
//                         {
//                             fieldname: "item_code",
//                             fieldtype: "Link",
//                             label: __("Item Code"),
//                             options: "Item",
//                             reqd: 1,
//                             read_only: 1,
//                             in_list_view: 1,
//                         },
//                         {
//                             fieldname: "warehouse",
//                             fieldtype: "Link",
//                             label: __("Warehouse"),
//                             options: "Warehouse",
//                             reqd: 1,
//                             in_list_view: 1,
//                         },
//                         {
//                             fieldname: "qty_to_reserve",
//                             fieldtype: "Float",
//                             label: __("Qty"),
//                             reqd: 1,
//                             in_list_view: 1,
//                         },
//                         {
//                             fieldname: "voucher_detail_no",
//                             fieldtype: "Data",
//                             label: __("Sales Order Item (voucher_detail_no)"),
//                             reqd: 1,
//                             read_only: 1,
//                             in_list_view: 1,
//                         },
                        
//                     ],
//                 },
//             ],
//             primary_action_label: __("Reserve Packed Items"),
//             primary_action: () => {
//                 const data = dialog.fields_dict.packed_items.grid.get_selected_children();
//                 if (data && data.length > 0) {
//                     // Include the parent (Sales Order ID) in each packed item
//                     data.forEach(item => {
//                         item.parent = frm.docname; // Set the Sales Order ID
//                     });
//                     console

//                     frappe.call({
//                         method: "sample_test.sample_test.override.reserve_so.create_packed_stock_reservation_entries",
//                         args: {
//                             items: data,
//                         },
//                         freeze: true,
//                         freeze_message: __("Reserving Packed Items Stock..."),
//                         callback: function(r) {
//                             frm.reload_doc();
//                             dialog.hide();
//                         },
//                     });
//                 } else {
//                     frappe.msgprint(__("Please select packed items to reserve."));
//                 }
//             },
//         });

//         // Populate all packed items into the dialog
//         frm.doc.packed_items.forEach((item) => {
//             let unreserved_qty = flt(item.qty) - flt(item.stock_reserved_qty || 0);
//             dialog.fields_dict.packed_items.df.data.push({
//                 packed_item: item.parent_item,
//                 item_code: item.item_code,
//                 warehouse: item.warehouse,
//                 qty_to_reserve: unreserved_qty,
//                 voucher_detail_no: item.packed_item ,
//                 // Pass Sales Order Item reference
//             });
//         });
        
//         dialog.fields_dict.packed_items.grid.refresh();
//         dialog.show();
//     },
// });
