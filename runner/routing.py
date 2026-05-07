from __future__ import annotations

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/job/(?P<job_id>\d+)/$", consumers.JobConsumer.as_asgi()),
]

