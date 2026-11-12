"""
urls.py - Konfigurasi URL utama proyek Smart Agriculture Hanjeli.

Routing utama:
  /                → Redirect ke halaman Kelola Sensor
  /admin/          → Django Admin bawaan
  /administrasi/   → Modul administrasi sensor, pot, penyiraman
"""

from django.contrib import admin
from django.urls import include, path
from admin.views import dashboard_main

urlpatterns = [
    # Landing page pada root proyek.
    path("", dashboard_main, name="dashboard_main"),

    # Django built-in admin panel
    path("admin/", admin.site.urls),

    # Modul administrasi Smart Agriculture
    path("administrasi/", include("admin.urls", namespace="administrasi")),
]
