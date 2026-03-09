"""WebSocket consumer for real-time agent action updates."""
from __future__ import annotations

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class AgentConsumer(AsyncJsonWebsocketConsumer):
    """Broadcast agent action state changes to circle members.

    Group name: ``circle_{circle_pk}_agents``
    """

    async def connect(self):
        self.circle_pk = self.scope["url_route"]["kwargs"]["circle_pk"]
        self.group_name = f"circle_{self.circle_pk}_agents"

        user = self.scope.get("user")
        if user is None or user.is_anonymous:
            await self.close()
            return

        is_member = await self._is_circle_member(user, self.circle_pk)
        if not is_member:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def agent_action_update(self, event: dict):
        """Handle ``agent.action.update`` type messages from the channel layer."""
        await self.send_json(event["payload"])

    @database_sync_to_async
    def _is_circle_member(self, user, circle_pk: str) -> bool:
        from circles.models import CircleMember

        return CircleMember.objects.filter(
            user=user, circle_id=circle_pk
        ).exists()
