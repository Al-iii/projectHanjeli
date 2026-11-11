
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('api/telemetry/latest/', views.latest_telemetry, name='latest_telemetry'),
]
