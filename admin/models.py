"""
models.py - Definisi model database untuk modul administrasi Smart Agriculture.

Berisi representasi tabel:
    - ControlBox       : Perangkat gateway IoT (ESP32) di lapangan.
    - SensorLingkungan : Sensor suhu udara dan intensitas cahaya.
    - SoilSensor       : Sensor kelembaban tanah multi-titik (3 titik).

Relasi:
    ControlBox ──< SensorLingkungan  (one-to-many)
    ControlBox ──< SoilSensor        (one-to-many)
"""

from django.db import models
from django.utils import timezone


class ControlBox(models.Model):
    """
    Merepresentasikan perangkat Control Box (ESP32 gateway IoT) di lapangan.

    Primary key menggunakan MAC Address perangkat sehingga bersifat unik
    secara global dan tidak memerlukan ID auto-increment tambahan.
    """

    STATUS_ONLINE  = "ONLINE"
    STATUS_OFFLINE = "OFFLINE"

    STATUS_CHOICES = [
        (STATUS_ONLINE,  "Online"),
        (STATUS_OFFLINE, "Offline"),
    ]

    mac_address = models.CharField(
        primary_key=True,
        max_length=17,
        verbose_name="MAC Address",
        help_text="Format: AA:BB:CC:DD:EE:FF",
    )
    nama = models.CharField(
        max_length=100,
        verbose_name="Nama Perangkat",
        help_text="Nama deskriptif untuk Control Box ini.",
    )
    status = models.CharField(
        max_length=7,
        choices=STATUS_CHOICES,
        default=STATUS_OFFLINE,
        verbose_name="Status Koneksi",
    )
    lokasi = models.CharField(
        max_length=255,
        verbose_name="Lokasi",
        help_text="Lokasi fisik pemasangan Control Box (mis. Kebun Blok A).",
    )
    terakhir_online = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Terakhir Online",
        help_text="Waktu terakhir perangkat mengirimkan data.",
    )
    dibuat_pada = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Dibuat Pada",
    )

    class Meta:
        verbose_name        = "Control Box"
        verbose_name_plural = "Control Boxes"
        ordering            = ["nama"]

    def __str__(self) -> str:
        """Representasi string: nama + MAC address + status."""
        return f"{self.nama} ({self.mac_address}) — {self.status}"

    def tandai_online(self) -> None:
        """
        Helper method untuk menandai perangkat sebagai ONLINE
        dan memperbarui timestamp terakhir_online.

        Gunakan method ini di mqtt_worker.py setiap kali pesan diterima:
            control_box.tandai_online()
        """
        self.status          = self.STATUS_ONLINE
        self.terakhir_online = timezone.now()
        self.save(update_fields=["status", "terakhir_online"])


class SensorLingkungan(models.Model):
    """
    Merepresentasikan sensor lingkungan (DHT22 + BH1750) yang mengukur
    suhu udara dan intensitas cahaya, terhubung ke sebuah Control Box.
    """

    id_sensor = models.AutoField(
        primary_key=True,
        verbose_name="ID Sensor",
    )
    id_box = models.ForeignKey(
        ControlBox,
        on_delete=models.CASCADE,
        related_name="sensor_lingkungan",
        verbose_name="Control Box",
        help_text="Control Box tempat sensor ini terhubung.",
    )
    suhu = models.FloatField(
        verbose_name="Suhu (°C)",
        help_text="Nilai suhu udara dalam derajat Celcius.",
    )
    intensitas_cahaya = models.FloatField(
        verbose_name="Intensitas Cahaya (lux)",
        help_text="Nilai intensitas cahaya dalam satuan lux.",
    )
    port = models.CharField(
        max_length=50,
        verbose_name="Port / Pin",
        help_text="Identifier port atau pin pada Control Box (mis. GPIO4, I2C).",
    )
    diperbarui_pada = models.DateTimeField(
        auto_now=True,
        verbose_name="Diperbarui Pada",
    )

    class Meta:
        verbose_name        = "Sensor Lingkungan"
        verbose_name_plural = "Sensor Lingkungan"
        ordering            = ["id_box", "id_sensor"]

    def __str__(self) -> str:
        """Representasi string: ID sensor dan nama Control Box induknya."""
        return f"Sensor Lingkungan #{self.id_sensor} → {self.id_box.nama}"


class SoilSensor(models.Model):
    """
    Merepresentasikan sensor kelembaban tanah (soil moisture kapasitif)
    dengan tiga titik pengukuran berbeda, terhubung ke sebuah Control Box.
    """

    id_soil = models.AutoField(
        primary_key=True,
        verbose_name="ID Soil Sensor",
    )
    id_box = models.ForeignKey(
        ControlBox,
        on_delete=models.CASCADE,
        related_name="soil_sensor",
        verbose_name="Control Box",
        help_text="Control Box tempat sensor ini terhubung.",
    )
    kelembaban_titik1 = models.FloatField(
        verbose_name="Kelembaban Titik 1 (%)",
        help_text="Nilai kelembaban tanah pada titik pengukuran pertama.",
    )
    kelembaban_titik2 = models.FloatField(
        verbose_name="Kelembaban Titik 2 (%)",
        help_text="Nilai kelembaban tanah pada titik pengukuran kedua.",
    )
    kelembaban_titik3 = models.FloatField(
        verbose_name="Kelembaban Titik 3 (%)",
        help_text="Nilai kelembaban tanah pada titik pengukuran ketiga.",
    )
    port = models.CharField(
        max_length=50,
        verbose_name="Port / Pin",
        help_text="Identifier pin ADC pada Control Box (mis. GPIO34/35/32).",
    )
    diperbarui_pada = models.DateTimeField(
        auto_now=True,
        verbose_name="Diperbarui Pada",
    )

    class Meta:
        verbose_name        = "Soil Sensor"
        verbose_name_plural = "Soil Sensors"
        ordering            = ["id_box", "id_soil"]

    def __str__(self) -> str:
        """Representasi string: ID soil sensor dan nama Control Box induknya."""
        return f"Soil Sensor #{self.id_soil} → {self.id_box.nama}"
