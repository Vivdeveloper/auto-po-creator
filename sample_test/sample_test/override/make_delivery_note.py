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
        delivered_qty_map[item.item_code] = delivered_qty_map.get(item.item_code, 0) + item.qty

    # Step 3: Fetch the Sales Order and calculate remaining quantities
    so = frappe.get_doc("Sales Order", source_name)
    target_doc = frappe.new_doc("Delivery Note")  # Start with a new Delivery Note
    target_doc.customer = so.customer  # Map Sales Order fields
    target_doc.posting_date = frappe.utils.today()

    for so_item in so.items:
        total_delivered_qty = delivered_qty_map.get(so_item.item_code, 0)
        remaining_qty = flt(so_item.qty) - flt(total_delivered_qty)

        if remaining_qty > 0:
            # Step 4: Check for reserved stock
            reserved_stock = get_sre_reserved_qty_details_for_voucher(
                so_item.item_code, source_name
            )
            
            reserved_qty = reserved_stock.get("reserved_qty", 0)
            unreserved_qty = remaining_qty - reserved_qty

            # Add reserved stock first
            if reserved_qty > 0:
                target_doc.append("items", {
                    "item_code": so_item.item_code,
                    "qty": reserved_qty,
                    "rate": so_item.rate,
                    "warehouse": so_item.warehouse,
                    "description": so_item.description or "Reserved Stock",
                    "against_sales_order": source_name,
                    "so_detail": so_item.name,  # Reference to the Sales Order Item
                })

            # Add unreserved stock next
            if unreserved_qty > 0:
                target_doc.append("items", {
                    "item_code": so_item.item_code,
                    "qty": unreserved_qty,
                    "rate": so_item.rate,
                    "warehouse": so_item.warehouse,
                    "description": so_item.description or "Unreserved Stock",
                    "against_sales_order": source_name,
                    "so_detail": so_item.name,  # Reference to the Sales Order Item
                })

    # Step 5: Calculate totals and set missing values
    target_doc.set_missing_values()
    target_doc.run_method("calculate_taxes_and_totals")

    return target_doc


@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, kwargs=None):
    from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
    from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
        get_sre_details_for_voucher,
        get_sre_reserved_qty_details_for_voucher,
        get_ssb_bundle_for_voucher,
    )
    from frappe.utils import flt, cstr
    from erpnext.stock.get_item_details import get_item_defaults, get_item_group_defaults
    from erpnext.accounts.party import get_company_address
    from frappe.contacts.doctype.address.address import get_address_display
    from frappe.model.mapper import get_mapped_doc

    if not kwargs:
        kwargs = {
            "for_reserved_stock": frappe.flags.args and frappe.flags.args.for_reserved_stock,
            "skip_item_mapping": frappe.flags.args and frappe.flags.args.skip_item_mapping,
        }

    kwargs = frappe._dict(kwargs)

    sre_details = {}
    if kwargs.for_reserved_stock:
        sre_details = get_sre_reserved_qty_details_for_voucher("Sales Order", source_name)

    mapper = {
        "Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
        "Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "add_if_empty": True},
        "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
    }

    def set_missing_values(source, target):
        target.run_method("set_missing_values")
        target.run_method("set_po_nos")
        target.run_method("calculate_taxes_and_totals")
        target.run_method("set_use_serial_batch_fields")

        if source.company_address:
            target.update({"company_address": source.company_address})
        else:
            # set company address
            target.update(get_company_address(target.company))

        if target.company_address:
            address_display = get_address_display(target.company_address)
            target.company_address_display = address_display

        # if invoked in bulk creation, validations are ignored and thus this method is never invoked
        if frappe.flags.bulk_transaction:
            # set target items names to ensure proper linking with packed_items
            target.set_new_name()

        make_packing_list(target)

    def condition(doc):
        # Fetch total delivered quantity from submitted Delivery Notes
        delivered_qty = frappe.db.sql("""
            SELECT SUM(qty) FROM `tabDelivery Note Item`
            WHERE so_detail = %s AND docstatus = 1
        """, doc.name)[0][0] or 0.0

        remaining_qty = flt(doc.qty) - delivered_qty - flt(doc.stock_reserved_qty)

        # Include the item if there is stock reserved or remaining quantity
        if remaining_qty <= 0 and flt(doc.stock_reserved_qty) <= 0:
            return False

        if frappe.flags.args and frappe.flags.args.delivery_dates:
            if cstr(doc.delivery_date) not in frappe.flags.args.delivery_dates:
                return False
        if frappe.flags.args and frappe.flags.args.until_delivery_date:
            if cstr(doc.delivery_date) > frappe.flags.args.until_delivery_date:
                return False

        return abs(delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier != 1

    def update_item(source, target, source_parent):
        # Fetch total delivered quantity from submitted Delivery Notes
        delivered_qty = frappe.db.sql("""
            SELECT SUM(qty) FROM `tabDelivery Note Item`
            WHERE so_detail = %s AND docstatus = 1
        """, source.name)[0][0] or 0.0

        reserved_qty = flt(source.stock_reserved_qty)
        remaining_qty = flt(source.qty) - delivered_qty - reserved_qty

        # Ensure remaining_qty is not negative
        if remaining_qty < 0:
            remaining_qty = 0

        target.base_amount = remaining_qty * flt(source.base_rate)
        target.amount = remaining_qty * flt(source.rate)
        target.qty = remaining_qty

        item = get_item_defaults(target.item_code, source_parent.company)
        item_group = get_item_group_defaults(target.item_code, source_parent.company)

        if item:
            target.cost_center = (
                frappe.db.get_value("Project", source_parent.project, "cost_center")
                or item.get("buying_cost_center")
                or item_group.get("buying_cost_center")
            )

    if not kwargs.skip_item_mapping:
        mapper["Sales Order Item"] = {
            "doctype": "Delivery Note Item",
            "field_map": {
                "rate": "rate",
                "name": "so_detail",
                "parent": "against_sales_order",
            },
            "condition": condition,
            "postprocess": update_item,
        }

    so = frappe.get_doc("Sales Order", source_name)
    target_doc = get_mapped_doc("Sales Order", so.name, mapper, target_doc)

    if not kwargs.skip_item_mapping and kwargs.for_reserved_stock:
        sre_list = get_sre_details_for_voucher("Sales Order", source_name)

        if sre_list:

            def update_dn_item(source, target, source_parent):
                # Fetch source_parent if it's None
                if not source_parent:
                    source_parent = frappe.get_doc("Sales Order", source.parent)

                # For reserved quantities, set the qty directly from the SRE
                target.base_amount = flt(target.qty) * flt(source.base_rate)
                target.amount = flt(target.qty) * flt(source.rate)

                item = get_item_defaults(target.item_code, source_parent.company)
                item_group = get_item_group_defaults(target.item_code, source_parent.company)

                if item:
                    target.cost_center = (
                        frappe.db.get_value("Project", source_parent.project, "cost_center")
                        or item.get("buying_cost_center")
                        or item_group.get("buying_cost_center")
                    )

            so_items = {d.name: d for d in so.items if d.stock_reserved_qty}

            for sre in sre_list:
                dn_item = get_mapped_doc(
                    "Sales Order Item",
                    sre.voucher_detail_no,
                    {
                        "Sales Order Item": {
                            "doctype": "Delivery Note Item",
                            "field_map": {
                                "rate": "rate",
                                "name": "so_detail",
                                "parent": "against_sales_order",
                            },
                            "postprocess": update_dn_item,
                        }
                    },
                    ignore_permissions=True,
                )

                dn_item.qty = flt(sre.reserved_qty) * flt(dn_item.get("conversion_factor", 1))

                # Set the warehouse from the Stock Reservation Entry
                dn_item.warehouse = sre.warehouse  # Ensure 'sre.warehouse' is correct

                if sre.reservation_based_on == "Serial and Batch" and (sre.has_serial_no or sre.has_batch_no):
                    dn_item.serial_and_batch_bundle = get_ssb_bundle_for_voucher(sre)

                target_doc.append("items", dn_item)
            else:
                # Correct rows index.
                for idx, item in enumerate(target_doc.items):
                    item.idx = idx + 1

    if not kwargs.skip_item_mapping and frappe.flags.bulk_transaction and not target_doc.items:
        # the (date) condition filter resulted in an unintendedly created empty DN; remove it
        del target_doc
        return

    # Should be called after mapping items.
    set_missing_values(so, target_doc)

    return target_doc












