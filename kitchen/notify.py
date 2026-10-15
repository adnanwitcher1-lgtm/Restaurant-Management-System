from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def group_name(branch_id):
    return f"branch_{branch_id}"


def notify_branch(branch):
    """Tell every open screen of this branch that orders changed.
    Accepts a Branch object or a branch id."""
    branch_id = getattr(branch, "pk", branch)
    layer = get_channel_layer()
    if layer is None or branch_id is None:
        return
    async_to_sync(layer.group_send)(group_name(branch_id), {"type": "orders.changed"})


order_changed = notify_branch  # same function, second name
