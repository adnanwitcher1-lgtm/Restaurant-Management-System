from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from branches.models import Branch

from .notify import group_name

ALLOWED_ROLES = ("Owner", "Manager", "Kitchen", "Waiter", "Cashier")


@database_sync_to_async
def _branch_id_for(user, session):
    if (
        not user.is_authenticated
        or not user.role
        or user.role.name not in ALLOWED_ROLES
    ):
        return None
    if user.role.name == "Owner":
        branches = Branch.objects.filter(is_active=True)
        branch = None
        branch_id = session.get("branch_id") if session else None
        if branch_id:
            branch = branches.filter(pk=branch_id).first()
        branch = branch or branches.first()
        return branch.pk if branch else None
    return user.branch_id


class OrdersConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.group = None
        branch_id = await _branch_id_for(self.scope["user"], self.scope.get("session"))
        if not branch_id:
            await self.close()
            return
        self.group = group_name(branch_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if self.group:
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def orders_changed(self, event):
        await self.send_json({"type": "orders_changed"})
