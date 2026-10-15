from django.db import transaction

from kitchen.notify import order_changed
from menu.models import MenuItem

from .models import Order, OrderItem

MAX_QTY = 50
MAX_LINES = 50

# current status -> statuses it may move to
TRANSITIONS = {
    Order.PENDING: {Order.PREPARING, Order.CANCELLED},
    Order.PREPARING: {Order.READY},
    Order.READY: {Order.SERVED},
}


class OrderError(Exception):
    """A problem with an order request. The message is safe to show to the user."""


def parse_items(branch, raw_items):
    """Validate [{id, qty, note}, ...] and return [(MenuItem, qty, note), ...]."""
    if not isinstance(raw_items, list) or not raw_items:
        raise OrderError("Add at least one item to the order.")
    if len(raw_items) > MAX_LINES:
        raise OrderError("Too many items in one order.")
    try:
        wanted = [
            (int(raw["id"]), int(raw["qty"]), str(raw.get("note", ""))[:200].strip())
            for raw in raw_items
        ]
    except (AttributeError, KeyError, TypeError, ValueError):
        raise OrderError("Invalid items in the order.")
    if any(qty < 1 or qty > MAX_QTY for _, qty, _ in wanted):
        raise OrderError("Quantity must be between 1 and 50.")

    menu_items = MenuItem.objects.filter(
        branch=branch,
        is_available=True,
        category__is_active=True,
        pk__in=[item_id for item_id, _, _ in wanted],
    )
    by_id = {item.pk: item for item in menu_items}
    if any(item_id not in by_id for item_id, _, _ in wanted):
        raise OrderError("Some items are no longer available. Please refresh the page.")
    return [(by_id[item_id], qty, note) for item_id, qty, note in wanted]


def add_lines(order, lines):
    # Name and price are copied so old orders never change when the menu does
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                menu_item=menu_item,
                name=menu_item.name,
                unit_price=menu_item.price,
                quantity=qty,
                note=note,
            )
            for menu_item, qty, note in lines
        ]
    )


@transaction.atomic
def create_order(branch, table, order_type, waiter, lines, note=""):
    order = Order.objects.create(
        branch=branch, table=table, order_type=order_type, waiter=waiter, note=note
    )
    add_lines(order, lines)
    transaction.on_commit(lambda: order_changed(order.branch_id))
    return order


@transaction.atomic
def add_items_to_order(order, lines):
    if order.status not in (Order.PENDING, Order.PREPARING):
        raise OrderError(
            "Items can only be added while the order is pending or preparing."
        )
    add_lines(order, lines)
    order.save(update_fields=["updated_at"])
    transaction.on_commit(lambda: order_changed(order.branch_id))
    return order


def change_status(order, new_status):
    """Move an order to new_status, but only along a valid path."""
    if new_status not in TRANSITIONS.get(order.status, set()):
        raise OrderError("That status change is not allowed for this order.")
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    transaction.on_commit(lambda: order_changed(order.branch_id))
    return order
