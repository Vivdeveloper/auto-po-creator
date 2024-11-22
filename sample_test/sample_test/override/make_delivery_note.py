# apps/sample_test/sample_test/sample_test/override/make_delivery_note.py

import frappe
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc  # Direct import
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder
import json
from typing import Literal

import frappe
import frappe.utils
from frappe import _, qb
from frappe.contacts.doctype.address.address import get_company_address
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, cint, cstr, flt, get_link_to_form, getdate, nowdate, strip_html
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)
from erpnext.accounts.party import get_party_account
from erpnext.controllers.selling_controller import SellingController
from erpnext.manufacturing.doctype.blanket_order.blanket_order import (
	validate_against_blanket_order,
)
from erpnext.manufacturing.doctype.production_plan.production_plan import (
	get_items_for_material_requests,
)
from erpnext.selling.doctype.customer.customer import check_credit_limit
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	get_sre_reserved_qty_details_for_voucher,
	has_reserved_stock,
)
from erpnext.stock.get_item_details import get_default_bom, get_price_list_rate
from erpnext.stock.stock_balance import get_reserved_qty, update_bin_qty

@frappe.whitelist()
def custom_make_delivery_note(source_name, target_doc=None, kwargs=None):
    from erpnext.stock.doctype.packed_item.packed_item import make_packing_list

    if not kwargs:
        kwargs = {
            "for_reserved_stock": frappe.flags.args and frappe.flags.args.for_reserved_stock,
            "skip_item_mapping": frappe.flags.args and frappe.flags.args.skip_item_mapping,
        }

    kwargs = frappe._dict(kwargs)

    # Step 1: Fetch all previous Delivery Note items linked to this Sales Order
    existing_delivery_note_items = frappe.get_all(
        "Delivery Note Item",
        filters={"against_sales_order": source_name},
        fields=["item_code", "qty"]
    )

    # Step 2: Initialize delivered_qty_map
    delivered_qty_map = frappe._dict()
    for item in existing_delivery_note_items:
        # Log each step of the update
        frappe.logger().info(f"Processing Item: {item.item_code}, Qty: {item.qty}")
        delivered_qty_map[item.item_code] = delivered_qty_map.get(item.item_code, 0) + item.qty
        frappe.logger().info(f"Updated delivered_qty_map: {delivered_qty_map}")

    # Log the final delivered_qty_map after the loop
    frappe.logger().info(f"Final delivered_qty_map: {delivered_qty_map}")

    # frappe.throw(f"Final delivered_qty_map: {delivered_qty_map}")
	

    # Step 3: Fetch the Sales Order and calculate remaining quantities
    so = frappe.get_doc("Sales Order", source_name)
    target_doc = frappe.new_doc("Delivery Note")  # Start with a new Delivery Note
    target_doc.customer = so.customer  # Map Sales Order fields
    target_doc.posting_date = frappe.utils.today()

    for so_item in so.items:
        total_delivered_qty = delivered_qty_map.get(so_item.item_code, 0)
        remaining_qty = flt(so_item.qty) - flt(total_delivered_qty)

        # Only add items with remaining quantities
        if remaining_qty > 0:
            target_doc.append("items", {
                "item_code": so_item.item_code,
                "qty": remaining_qty,
                "rate": so_item.rate,
                "warehouse": so_item.warehouse,
                "description": so_item.description or "Sales Order Item",
                "against_sales_order": source_name,
                "so_detail": so_item.name,  # Reference to the Sales Order Item
            })

    # Step 4: Calculate totals and set missing values
    target_doc.set_missing_values()
    target_doc.run_method("calculate_taxes_and_totals")

    return target_doc








