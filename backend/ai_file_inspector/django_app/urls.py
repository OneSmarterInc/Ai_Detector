from django.urls import path

from . import views

app_name = "ai_file_inspector"
urlpatterns = [
    path("info/", views.info, name="info"),
    path("jobs/", views.jobs, name="jobs"),
    path("jobs/<uuid:job_id>/", views.job_detail, name="job-detail"),
    path("jobs/<uuid:job_id>/report/", views.report_download, name="report"),
    path("jobs/<uuid:job_id>/assets/<str:name>", views.asset, name="asset"),
]
