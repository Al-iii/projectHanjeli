from django.urls import path
from . import views

app_name = 'prediktor'

urlpatterns = [
    path('tanaman-jagung/', views.deteksi_tanaman_jagung, name='deteksi_tanaman_jagung'),
    path('jagung/', views.deteksi_jagung, name='deteksi_jagung'),
    path('', views.beranda, name='beranda'),
]
