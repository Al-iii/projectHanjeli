
"""
urls.py - Konfigurasi URL utama proyek Smart Agriculture Hanjeli.
"""

from django.contrib import admin
from django.urls import include, path
from admin.views import dashboard_main
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    # Dashboard utama
    path("", include("dashboard.urls")),

    # Dashboard administrasi
    path("admin-dashboard/", dashboard_main, name="dashboard_main"),

    # Dashboard modul lainnya
    path("main-dashboard/", include("dashboard.urls")),

    # Django Admin
    path("admin/", admin.site.urls),

    # Modul administrasi Smart Agriculture
    path("administrasi/", include("admin.urls", namespace="administrasi")),
    
    path('prediktor/', include('prediktor.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)