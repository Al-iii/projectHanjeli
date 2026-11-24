
from django.db import models


class Telemetry(models.Model):
    # Identitas perangkat
    device_id = models.CharField(max_length=100)

    # Data lingkungan
    temperature = models.FloatField(null=True, blank=True)
    air_humidity = models.FloatField(null=True, blank=True)
    soil_adc = models.IntegerField(null=True, blank=True)
    lux = models.FloatField(null=True, blank=True)

    # Status penyiraman
    valve = models.BooleanField(null=True, blank=True)
    pump = models.BooleanField(null=True, blank=True)
    state = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=50, blank=True)

    # Informasi aliran air
    flow_lpm = models.FloatField(null=True, blank=True)
    total_liter = models.FloatField(null=True, blank=True)

    # Informasi perangkat
    wifi_rssi = models.IntegerField(null=True, blank=True)
    uptime_s = models.PositiveBigIntegerField(null=True, blank=True)

    # Waktu data diterima
    received_at = models.DateTimeField(auto_now_add=True)

    # Menyimpan payload JSON asli
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        return f"{self.device_id} - {self.received_at}"
