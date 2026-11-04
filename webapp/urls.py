from django.urls import path,re_path
from portal import views
urlpatterns=[
    path('api/info/',views.info),
    path('api/jobs/',views.jobs),
    path('api/jobs/<uuid:job_id>/',views.job_detail),
    path('api/jobs/<uuid:job_id>/report/',views.report_download),
    path('api/jobs/<uuid:job_id>/assets/<str:name>',views.asset),
    re_path(r'^(?P<path>.*)$',views.frontend),
]
