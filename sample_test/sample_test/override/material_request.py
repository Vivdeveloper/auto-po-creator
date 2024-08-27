import frappe
from frappe.model.document import Document

@frappe.whitelist()
def create_purchase_orders(material_request):
    material_request_doc = frappe.get_doc('Material Request', material_request)
    items_by_supplier = {}

    # Group items by supplier
    for item in material_request_doc.items:
        default_suppliers = frappe.get_all('Default Supplier', filters={'parent': item.item_code}, fields=['default_suppliers'])
        
        if not default_suppliers:
            frappe.throw(f"Please mention default supplier for item {item.item_code}")
        
        supplier = default_suppliers[0].default_suppliers  # Only take the first default supplier
        if supplier:
            if supplier not in items_by_supplier:
                items_by_supplier[supplier] = []
            items_by_supplier[supplier].append(item)

    # Create Purchase Orders for each supplier
    purchase_orders = []
    existing_orders = []
    updated_orders = []
    for supplier, items in items_by_supplier.items():
        # Get existing purchase orders for the supplier and material request
        existing_po_names = frappe.get_all('Purchase Order', filters={
            'material_request': material_request,
            'supplier': supplier,
            'docstatus': ['<', 2]  # Check for draft and submitted POs
        }, fields=['name'])

        ordered_qty_by_item = {}
        
        if existing_po_names:
            # Fetch all items in existing POs for the specific Material Request
            existing_po_items = frappe.get_all('Purchase Order Item', filters={
                'parent': ['in', [po.name for po in existing_po_names]],
                'material_request': material_request
            }, fields=['item_code', 'qty', 'material_request_item'])

            # Calculate ordered quantities by item code for the current Material Request
            for item in existing_po_items:
                if item['material_request_item'] in [i.name for i in items]:  # Ensure the item is part of the current Material Request
                    if item['item_code'] not in ordered_qty_by_item:
                        ordered_qty_by_item[item['item_code']] = 0
                    ordered_qty_by_item[item['item_code']] += item['qty']

        items_to_order = []
        for item in items:
            due_qty = item.qty - ordered_qty_by_item.get(item.item_code, 0)
            if due_qty > 0:
                item.due_qty = due_qty
                items_to_order.append(item)

        if items_to_order:
            # Check if there is an existing draft PO for this supplier
            existing_draft_po = frappe.db.exists('Purchase Order', {
                'supplier': supplier,
                'docstatus': 0,
                'material_request': material_request
            })
            
            if existing_draft_po:
                po = frappe.get_doc('Purchase Order', existing_draft_po)
                
                for item in items_to_order:
                    po.append('items', {
                        'item_code': item.item_code,
                        'qty': item.due_qty,
                        'schedule_date': item.schedule_date,
                        'rate': item.rate,
                        'warehouse': item.warehouse,
                        'material_request': material_request,
                        'material_request_item': item.name
                    })

                # Add taxes and charges
                add_taxes_and_charges(po)

                po.save()
                updated_orders.append({'name': po.name, 'supplier': po.supplier})
            else:
                po = frappe.new_doc('Purchase Order')
                po.supplier = supplier
                po.taxes_and_charges = "Input GST In-state - K"
                for item in items_to_order:
                    po.append('items', {
                        'item_code': item.item_code,
                        'qty': item.due_qty,
                        'schedule_date': item.schedule_date,
                        'rate': item.rate,
                        'warehouse': item.warehouse,
                        'material_request': material_request,
                        'material_request_item': item.name
                    })

                # Add taxes and charges
                add_taxes_and_charges(po)

                po.insert()
                purchase_orders.append({'name': po.name, 'supplier': po.supplier})
        else:
            if existing_po_names:
                existing_orders.append({'supplier': supplier, 'po_name': existing_po_names[0]})

    return {
        'created': purchase_orders,
        'existing': existing_orders,
        'updated': updated_orders
    }

def add_taxes_and_charges(po):
    """Add taxes and charges based on the 'taxes_and_charges' field."""
    if po.taxes_and_charges:
        taxes_template = frappe.get_doc('Purchase Taxes and Charges Template', po.taxes_and_charges)
        for tax in taxes_template.taxes:
            po.append('taxes', {
                'category': tax.category,
                'add_deduct_tax': tax.add_deduct_tax,
                'charge_type': tax.charge_type,
                'included_in_print_rate': tax.included_in_print_rate,
                'included_in_paid_amount': tax.included_in_paid_amount,
                'rate': tax.rate,
                'account_head': tax.account_head,
                'description': tax.description,
                'is_tax_withholding_account': tax.is_tax_withholding_account,
                'cost_center': tax.cost_center,
                'tax_amount': tax.tax_amount,
                'tax_amount_after_discount_amount': tax.tax_amount_after_discount_amount,
                'total': tax.total,
                'base_tax_amount': tax.base_tax_amount,
                'base_tax_amount_after_discount_amount': tax.base_tax_amount_after_discount_amount,
                'base_total': tax.base_total
            })





@frappe.whitelist()
def get_suppliers_for_item(item_code):
    default_suppliers = frappe.get_all('Default Supplier', filters={'parent': item_code}, fields=['default_suppliers'])
    supplier_list = [entry.default_suppliers for entry in default_suppliers]
    return supplier_list
