__version__ = "0.0.1"

import frappe
from frappe import _ 
import json
from erpnext.manufacturing.doctype.production_plan import production_plan
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

def custom_get_items_for_material_requests(doc, warehouses=None, get_parent_warehouse_data=None):
    # Ensure doc is parsed as a dict; if it's a string, load it as JSON
    if isinstance(doc, str):
        doc = json.loads(doc)
    
    # Convert to frappe._dict to access safely
    doc = frappe._dict(doc)

    company = doc.get("company")
    mr_items = []

    # Get the items from the doc (which is a list of items)
    po_items = doc.get("po_items") if doc.get("po_items") else doc.get("items")
    print(po_items)

    # Check if there are items present
    if not po_items or not [row.get("item_code") for row in po_items if row.get("item_code")]:
        frappe.throw(_("Items to Manufacture are required to pull the Raw Materials associated with it."), title=_("Items Required"))

    for data in po_items:
        # Fetch the required_qty from the nested item field
        planned_qty = data.get("required_qty") or data.get("planned_qty")
        print(planned_qty)

        # Remove warehouse filter, sum actual_qty across all warehouses for the item
        total_actual_qty = frappe.db.sql("""
            SELECT SUM(actual_qty)
            FROM `tabBin`
            WHERE item_code=%s
        """, data.get("item_code"))[0][0] or 0
        print(f"{total_actual_qty}: actual_qty for {data.get('item_code')}")

        # Compare the required quantity against total stock across all warehouses
        if planned_qty > total_actual_qty:
            required_qty_for_request = planned_qty - total_actual_qty
        else:
            required_qty_for_request = 0

        # If BOM exists, fetch the BOM items
        if data.get("bom"):
            bom_items = frappe.get_all("BOM Item", filters={"parent": data.get("bom")}, fields=["item_code", "qty", "stock_uom"])

            # Add each BOM item to Material Request based on the planned quantity
            for bom_item in bom_items:
                total_required_qty = bom_item.qty * planned_qty
                bom_actual_qty = frappe.db.sql("""
                    SELECT SUM(actual_qty)
                    FROM `tabBin`
                    WHERE item_code=%s
                """, bom_item.item_code)[0][0] or 0
                print(f"{bom_actual_qty}: actual_qty for BOM item {bom_item.item_code}")

                if total_required_qty > bom_actual_qty:
                    required_bom_qty = total_required_qty - bom_actual_qty
                    mr_items.append({
                        "item_code": bom_item.item_code,
                        "quantity": required_bom_qty,
                        "warehouse": data.get("warehouse"),  # Keep the warehouse for MR purposes
                        "stock_uom": bom_item.stock_uom
                    })
        else:
            # If no BOM, just add the current item to Material Request
            if required_qty_for_request > 0:
                mr_items.append({
                    "item_code": data.get("item_code"),
                    "quantity": required_qty_for_request,
                    "warehouse": data.get("warehouse")
                })

    # If no items are added to the Material Request, show a message
    if not mr_items:
        frappe.msgprint(_("No Material Request created as sufficient stock is available."))
    print(mr_items)

    return mr_items




def get_exploded_items(item_details, company, bom_no, include_non_stock_items, planned_qty=1, doc=None):
	bei = frappe.qb.DocType("BOM Explosion Item")
	bom = frappe.qb.DocType("BOM")
	item = frappe.qb.DocType("Item")
	item_default = frappe.qb.DocType("Item Default")
	item_uom = frappe.qb.DocType("UOM Conversion Detail")

	data = (
		frappe.qb.from_(bei)
		.join(bom)
		.on(bom.name == bei.parent)
		.join(item)
		.on(item.name == bei.item_code)
		.left_join(item_default)
		.on((item_default.parent == item.name) & (item_default.company == company))
		.left_join(item_uom)
		.on((item.name == item_uom.parent) & (item_uom.uom == item.purchase_uom))
		.select(
			(IfNull(Sum(bei.stock_qty / IfNull(bom.quantity, 1)), 0) * planned_qty).as_("qty"),
			item.item_name,
			item.name.as_("item_code"),
			bei.description,
			bei.stock_uom,
			item.min_order_qty,
			bei.source_warehouse,
			item.default_material_request_type,
			item.min_order_qty,
			item_default.default_warehouse,
			item.purchase_uom,
			item_uom.conversion_factor,
			item.safety_stock,
		)
		.where(
			(bei.docstatus < 2)
			& (bom.name == bom_no)
			& (item.is_stock_item.isin([0, 1]) if include_non_stock_items else item.is_stock_item == 1)
		)
		.groupby(bei.item_code, bei.stock_uom)
	).run(as_dict=True)

	for d in data:
		if not d.conversion_factor and d.purchase_uom:
			d.conversion_factor = get_uom_conversion_factor(d.item_code, d.purchase_uom)
		item_details.setdefault(d.get("item_code"), d)

	return item_details

def get_uom_conversion_factor(item_code, uom):
	return frappe.db.get_value(
		"UOM Conversion Detail", {"parent": item_code, "uom": uom}, "conversion_factor"
	)

# Override the default method
# setattr(production_plan, "get_items_for_material_requests", custom_get_items_for_material_requests)


# Helper function to get warehouse list
# def get_warehouse_list(warehouses):
#     warehouse_list = []

#     if isinstance(warehouses, str):
#         warehouses = json.loads(warehouses)

#     for row in warehouses:
#         child_warehouses = frappe.db.get_descendants("Warehouse", row.get("warehouse"))
#         if child_warehouses:
#             warehouse_list.extend(child_warehouses)
#         else:
#             warehouse_list.append(row.get("warehouse"))

#     return warehouse_list

# # Use setattr to override the function
# setattr(production_plan, "get_items_for_material_requests", custom_get_items_for_material_requests)





