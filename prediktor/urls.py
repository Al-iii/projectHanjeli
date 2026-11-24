from django.urls import path
from . import views

app_name = 'prediktor'

urlpatterns = [
    path('jagung/', views.deteksi_jagung, name='deteksi_jagung'),
    path('', views.beranda, name='beranda'),
]
