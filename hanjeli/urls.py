
"""
urls.py - Konfigurasi URL utama proyek Smart Agriculture Hanjeli.
"""

from django.contrib import admin
from django.urls import include, path
from admin.views import dashboard_main
from dashboard.views import index as monitoring_dashboard
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    # Dashboard utama
    path("", include("dashboard.urls")),

    # Dashboard administrasi
    path("admin-dashboard/", dashboard_main),
    path("admin", monitoring_dashboard, name="dashboard_main"),
    path("admin/", monitoring_dashboard, name="dashboard_monitoring_slash"),

    # Dashboard modul lainnya
    path("main-dashboard/", include("dashboard.urls")),

    # Django Admin
    path("django-admin/", admin.site.urls),

    # Modul administrasi Smart Agriculture
    path("admin/sensor/", include("admin.urls", namespace="administrasi")),
    
    path('prediktor/', include('prediktor.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
