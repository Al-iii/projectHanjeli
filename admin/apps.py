"""apps.py - Konfigurasi aplikasi modul Administrasi Smart Agriculture."""

from django.apps import AppConfig


class AdminConfig(AppConfig):
    """Konfigurasi app administrasi Smart Agriculture."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "admin"
    # Label unik agar tidak bentrok dengan django.contrib.admin
    label = "administrasi"
    verbose_name = "Administrasi Smart Agriculture"
