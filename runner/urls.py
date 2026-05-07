from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("overview/", views.overview, name="overview"),
    path("dsl/<str:dsl>/", views.dsl_page, name="dsl_page"),
    path("job/<int:job_id>/", views.job_detail, name="job_detail"),
    path("job/<int:job_id>/status/", views.job_status, name="job_status"),
    path("job/<int:job_id>/cancel/", views.job_cancel, name="job_cancel"),
    path("job/<int:job_id>/download/<str:kind>/", views.job_download, name="job_download"),
    path("job/<int:job_id>/input/", views.job_input_list, name="job_input_list"),
    path("job/<int:job_id>/input/<str:name>/", views.job_input_file, name="job_input_file"),
    path("dsl/<str:dsl>/run-example/", views.run_example, name="run_example"),
]

