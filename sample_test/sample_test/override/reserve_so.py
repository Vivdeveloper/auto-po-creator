import frappe
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
    create_stock_reservation_entries_for_so_items
)

@frappe.whitelist()
def create_packed_stock_reservation_entries(items):
    """Handles stock reservation for packed items."""
    # Parse the items if they are passed as a string
    if isinstance(items, str):
        items = frappe.parse_json(items)
    
    

    # Check if items are passed
    if not items:
        frappe.throw("No packed items provided for stock reservation")
    

    # Iterate through the packed items
    for item in items:
        # Fetch the Sales Order document using the parent field (Sales Order ID)
        sales_order = frappe.get_doc("Sales Order", item.get("parent"))
        sales_order_name = frappe.db.get_value("Sales Order Item",{"parent":sales_order.name,"item_code":item.get("packed_item")},"name")
       
        
        if not sales_order:
            frappe.throw("Sales Order not found")

        # Fetch the related Sales Order Item (voucher_detail_no)
        voucher_detail_no = item.get("voucher_detail_no")
        # if not voucher_detail_no:
        #     frappe.throw("Sales Order Item (voucher_detail_no) not found for packed item: {0}".format(item.get("item_code")))

        # Create stock reservation entry for each packed item
        create_stock_reservation_entries_for_so_items(
            sales_order=sales_order,  # Pass the Sales Order document
            items_details=[{
                '__checked': 1,
                'sales_order_item': sales_order_name,
                "item_code": item.get("item_code"),
                "warehouse": item.get("warehouse"),
                "qty_to_reserve": item.get("qty_to_reserve"),
                'idx': 1, 'name': 'row 1'  
            }],
        )
