"""Feeds the Ecommerce Core dashboard with Unicommerce orders, payments and stock pushes."""

import frappe
from ecommerce_core.dashboard import queries
from ecommerce_core.dashboard.adapter import DashboardAdapter
from frappe import _

from unicommerce.unicommerce.constants import IS_COD_CHECKBOX, ORDER_CODE_FIELD, SETTINGS_DOCTYPE

# Older than any Bin.modified, so the next inventory run picks the item up.
STALE_SYNC_TIMESTAMP = "2000-01-01 00:00:00"


class UnicommerceDashboardAdapter(DashboardAdapter):
	def is_enabled(self) -> bool:
		return frappe.get_cached_doc(SETTINGS_DOCTYPE).is_enabled()

	def get_recent_orders(self, limit, search=None, status=None):
		return queries.recent_sales_orders(ORDER_CODE_FIELD, limit, search, status)

	def count_orders(self, search=None, status=None):
		return queries.count_sales_orders(ORDER_CODE_FIELD, search, status)

	def get_pending_payments(self, limit, search=None, status=None):
		return queries.pending_sales_invoices(
			ORDER_CODE_FIELD, limit, search, status, cod_field=IS_COD_CHECKBOX
		)

	def count_pending_payments(self, search=None, status=None):
		return queries.count_pending_sales_invoices(
			ORDER_CODE_FIELD, search, status, cod_field=IS_COD_CHECKBOX
		)

	def get_pending_summary(self):
		return queries.pending_sales_invoice_summary(ORDER_CODE_FIELD)

	def push_inventory(self, ecommerce_items):
		settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
		if not settings.enable_inventory_sync:
			frappe.throw(_("Inventory sync is disabled in Unicommerce Settings."))

		for name in ecommerce_items:
			frappe.db.set_value(
				"Ecommerce Item", name, "inventory_synced_on", STALE_SYNC_TIMESTAMP, update_modified=False
			)

		frappe.enqueue(
			"unicommerce.unicommerce.inventory.update_inventory_on_unicommerce",
			queue="short",
			job_id="unicommerce_dashboard_inventory_push",
			deduplicate=True,
			force=True,
			enqueue_after_commit=True,
		)
		return _("Stock push to Unicommerce queued")
