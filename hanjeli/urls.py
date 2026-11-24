
"""
urls.py - Konfigurasi URL utama proyek Smart Agriculture Hanjeli.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Dashboard utama (/) dan API telemetry. Include hanya sekali agar
    # nama route dashboard_main/latest_telemetry tidak terdaftar berulang.
    path("", include("dashboard.urls")),

    # Modul sensor dan CRUD pot memiliki prefix tersendiri.
    path("sensor/", include("admin.urls", namespace="administrasi")),

    # Django Admin terpisah dari dashboard monitoring.
    path("django-admin/", admin.site.urls),
    path("prediktor/", include("prediktor.urls")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
