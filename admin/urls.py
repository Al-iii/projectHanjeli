"""
urls.py - Konfigurasi URL untuk modul administrasi Smart Agriculture Hanjeli.

Semua URL modul administrasi diawali dengan prefix 'administrasi/'
yang didefinisikan di urls.py tingkat proyek (hanjeli/urls.py).
"""

from django.urls import path

from . import views

# Namespace untuk reverse URL, contoh: reverse('administrasi:kelola_sensor')
app_name = "administrasi"

urlpatterns = [
    # Halaman daftar & kelola sensor
    # URL lengkap: /administrasi/sensor/
    path(
        "sensor/",
        views.kelola_sensor,
        name="kelola_sensor",
    ),

    # --- Placeholder untuk fitur mendatang ---
    # path("pot/",        views.kelola_pot,        name="kelola_pot"),
    # path("penyiraman/", views.kelola_penyiraman,  name="kelola_penyiraman"),
]

