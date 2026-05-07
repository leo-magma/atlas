from __future__ import annotations

import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from .models import RunJob


class JobConsumer(AsyncWebsocketConsumer):
    def _session_can_access_job(self) -> bool:
        if not settings.SUITEUI_REQUIRE_JOB_SESSION:
            return True
        raw = self.scope.get("session", {}).get("suiteui_job_ids", [])
        try:
            return self.job_id in {int(x) for x in raw}
        except Exception:
            return False

    async def connect(self):
        self.job_id = int(self.scope["url_route"]["kwargs"]["job_id"])
        self.group_name = f"job_{self.job_id}"
        if not self._session_can_access_job():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send initial snapshot
        try:
            job = await sync_to_async(RunJob.objects.get)(id=self.job_id)
        except RunJob.DoesNotExist:
            await self.close(code=4404)
            return
        await self.send(
            text_data=json.dumps(
                {
                    "type": "snapshot",
                    "id": job.id,
                    "dsl": job.dsl,
                    "status": job.status,
                    "progress": job.progress,
                    "output_text": job.output_text,
                    "error_text": job.error_text,
                }
            )
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def job_update(self, event):
        # Forward updates to the client
        await self.send(text_data=json.dumps(event["payload"]))

