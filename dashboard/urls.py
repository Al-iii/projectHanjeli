
from django.urls import path
from admin.views import dashboard_main

from . import views

urlpatterns = [
    # Root memakai view yang menyediakan telemetry, histori, dan data grafik.
    path('', dashboard_main, name='dashboard_main'),
    path('api/telemetry/latest/', views.latest_telemetry, name='latest_telemetry'),
]
