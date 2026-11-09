"""
admin.py - Konfigurasi tampilan Django Admin untuk modul administrasi Smart Agriculture.

Mendaftarkan model ControlBox, SensorLingkungan, dan SoilSensor ke antarmuka
Django Admin dengan konfigurasi list_display, search_fields, dan list_filter
agar pengelolaan data lebih efisien.
"""

from django.contrib import admin

from .models import ControlBox, SensorLingkungan, SoilSensor


@admin.register(ControlBox)
class ControlBoxAdmin(admin.ModelAdmin):
    """
    Konfigurasi admin untuk model ControlBox.

    Menampilkan kolom MAC Address, nama, status, dan lokasi pada daftar
    perangkat, serta mendukung pencarian dan pemfilteran berdasarkan status.
    """

    list_display = ("mac_address", "nama", "status", "lokasi")
    list_filter = ("status",)
    search_fields = ("mac_address", "nama", "lokasi")
    ordering = ("nama",)

    # Kelompokkan field di halaman detail/edit
    fieldsets = (
        (
            "Identitas Perangkat",
            {
                "fields": ("mac_address", "nama", "lokasi"),
            },
        ),
        (
            "Status Koneksi",
            {
                "fields": ("status",),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(SensorLingkungan)
class SensorLingkunganAdmin(admin.ModelAdmin):
    """
    Konfigurasi admin untuk model SensorLingkungan.

    Menampilkan ID sensor, Control Box induk, nilai suhu,
    intensitas cahaya, dan port pada daftar sensor lingkungan.
    """

    list_display = ("id_sensor", "id_box", "suhu", "intensitas_cahaya", "port")
    list_filter = ("id_box",)
    search_fields = ("id_box__nama", "id_box__mac_address", "port")
    ordering = ("id_box", "id_sensor")
    autocomplete_fields = ("id_box",)

    fieldsets = (
        (
            "Koneksi Perangkat",
            {
                "fields": ("id_box", "port"),
            },
        ),
        (
            "Data Pembacaan Sensor",
            {
                "fields": ("suhu", "intensitas_cahaya"),
            },
        ),
    )


@admin.register(SoilSensor)
class SoilSensorAdmin(admin.ModelAdmin):
    """
    Konfigurasi admin untuk model SoilSensor.

    Menampilkan ID soil sensor, Control Box induk, ketiga nilai kelembaban
    tanah, dan port pada daftar sensor kelembaban.
    """

    list_display = (
        "id_soil",
        "id_box",
        "kelembaban_titik1",
        "kelembaban_titik2",
        "kelembaban_titik3",
        "port",
    )
    list_filter = ("id_box",)
    search_fields = ("id_box__nama", "id_box__mac_address", "port")
    ordering = ("id_box", "id_soil")
    autocomplete_fields = ("id_box",)

    fieldsets = (
        (
            "Koneksi Perangkat",
            {
                "fields": ("id_box", "port"),
            },
        ),
        (
            "Data Kelembaban Tanah",
            {
                "fields": (
                    "kelembaban_titik1",
                    "kelembaban_titik2",
                    "kelembaban_titik3",
                ),
            },
        ),
    )
