"""Catat transisi penyiraman dari jalur penyimpanan telemetry yang sudah ada."""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from mqtt_receiver.models import Telemetry

from .models import Device, LogPenyiraman


def _pemicu_perangkat(payload):
    """Jangan menganggap ADC kering sebagai bukti penyiraman otomatis."""
    if not isinstance(payload, dict):
        return "Tidak dilaporkan perangkat"
    for key in ("trigger", "reason", "mode"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            value = value.strip()
            labels = {
                "manual": "Manual",
                "auto": "Otomatis",
                "automatic": "Otomatis",
                "dry_soil": "Otomatis (Tanah Kering)",
            }
            return labels.get(value.lower(), value)[:255]
    return "Tidak dilaporkan perangkat"


@receiver(post_save, sender=Telemetry, dispatch_uid="administrasi.log_penyiraman")
def catat_log_penyiraman(sender, instance, created, raw=False, using="default", **kwargs):
    """Satu log awal, lalu log hanya ketika pompa, valve, atau pemicu berubah."""
    if raw or not created:
        return
    # Null berarti belum diketahui, bukan OFF. Tunggu laporan yang lengkap.
    if instance.pump is None or instance.valve is None:
        return

    pemicu = _pemicu_perangkat(instance.raw_payload)
    with transaction.atomic(using=using):
        device, _ = Device.objects.using(using).get_or_create(
            device_id=instance.device_id
        )
        # Kunci perangkat bila database mendukung row locking.
        Device.objects.using(using).select_for_update().get(pk=device.pk)
        previous = LogPenyiraman.objects.using(using).filter(
            identitas_perangkat=instance.device_id
        ).first()
        if previous and (
            previous.pump, previous.valve, previous.pemicu
        ) == (instance.pump, instance.valve, pemicu):
            return

        adc = instance.soil_adc
        LogPenyiraman.objects.using(using).create(
            device=device,
            identitas_perangkat=instance.device_id,
            kode_pot=list(device.pots.using(using).values_list("kode_pot", flat=True)),
            telemetry=instance,
            waktu=instance.received_at,
            status="ON" if instance.pump or instance.valve else "OFF",
            pump=instance.pump,
            valve=instance.valve,
            pemicu=pemicu,
            keterangan=(
                "Status awal teramati" if previous is None else "Perubahan status/pemicu"
            ),
            adc=adc if adc is not None and adc >= 0 else None,
        )
