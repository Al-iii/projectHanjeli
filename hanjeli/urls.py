"""
urls.py - Konfigurasi URL utama proyek Smart Agriculture Hanjeli.

Routing utama:
  /                → Redirect ke halaman Kelola Sensor
  /admin/          → Django Admin bawaan
  /administrasi/   → Modul administrasi sensor, pot, penyiraman
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # Redirect root "/" ke halaman utama Kelola Sensor
    path(
        "",
        RedirectView.as_view(pattern_name="administrasi:kelola_sensor", permanent=False),
    ),

    # Django built-in admin panel
    path("admin/", admin.site.urls),

    # Modul administrasi Smart Agriculture
    path("administrasi/", include("admin.urls", namespace="administrasi")),
]
