import frappe
from frappe.model.document import Document

@frappe.whitelist()
def create_purchase_orders(material_request):
    material_request_doc = frappe.get_doc('Material Request', material_request)
    items_by_supplier = {}

    # Group items by supplier
    for item in material_request_doc.items:
        default_suppliers = frappe.get_all('Default Supplier', filters={'parent': item.item_code}, fields=['default_suppliers'])
        for entry in default_suppliers:
            supplier = entry.default_suppliers
            if supplier:
                if supplier not in items_by_supplier:
                    items_by_supplier[supplier] = []
                items_by_supplier[supplier].append(item)

    # Create Purchase Orders for each supplier
    purchase_orders = []
    existing_orders = []
    for supplier, items in items_by_supplier.items():
        existing_po = frappe.get_all('Purchase Order', filters={
            'material_request': material_request,
            'supplier': supplier,
            'docstatus': ['<', 2]  # Check for draft and submitted POs
        }, fields=['name'])

        if existing_po:
            existing_orders.append({'supplier': supplier, 'po_name': existing_po[0].name})
            continue 

        po = frappe.new_doc('Purchase Order')
        po.supplier = supplier
        for item in items:
            po.append('items', {
                'item_code': item.item_code,
                'qty': item.qty,
                'schedule_date': item.schedule_date,
                'rate': item.rate,
                'warehouse': item.warehouse,
                'material_request': material_request,
                'material_request_item': item.name
            })
        po.insert()
        purchase_orders.append({'name': po.name, 'supplier': po.supplier})

    return {
        'created': purchase_orders,
        'existing': existing_orders
    }


@frappe.whitelist()
def get_suppliers_for_item(item_code):
    default_suppliers = frappe.get_all('Default Supplier', filters={'parent': item_code}, fields=['default_suppliers'])
    supplier_list = [entry.default_suppliers for entry in default_suppliers]
    return supplier_list

