from django.urls import path
from . import views

app_name = 'prediktor'

urlpatterns = [
    path('', views.beranda, name='beranda'),
]