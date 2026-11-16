"""
urls.py - Konfigurasi URL utama proyek Smart Agriculture Hanjeli.
"""

from django.contrib import admin
from django.urls import include, path
from admin.views import dashboard_main

urlpatterns = [
    # Dashboard utama
    path("", include("dashboard.urls")),
    path("admin-dashboard/", dashboard_main, name="dashboard_main"),

    # Dashboard modul lainnya
    path("main-dashboard/", include("dashboard.urls")),

    # Django Admin
    path("admin/", admin.site.urls),

    # Modul administrasi Smart Agriculture
    path("administrasi/", include("admin.urls", namespace="administrasi")),
]