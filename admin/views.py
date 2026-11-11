"""View dashboard Modul Administrasi Smart Agriculture."""

from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render

from .models import DataSoil, DataWeather, Device


def _get_devices_with_latest_data():
    """Load devices and their latest weather and soil snapshots efficiently."""
    devices = list(
        Device.objects.prefetch_related(
            Prefetch(
                "weather_data",
                queryset=DataWeather.objects.order_by("-diperbarui_pada"),
                to_attr="weather_terbaru",
            ),
            Prefetch(
                "soil_data",
                queryset=DataSoil.objects.order_by("address"),
                to_attr="soil_terbaru",
            ),
        )
    )

    for device in devices:
        device.weather = device.weather_terbaru[0] if device.weather_terbaru else None
        device.soil = device.soil_terbaru
    return devices


def kelola_sensor(request):
    """Ambil perangkat beserta snapshot weather dan soil terakhirnya."""
    devices = _get_devices_with_latest_data()

    total = len(devices)
    online = sum(device.status_koneksi == Device.STATUS_ONLINE for device in devices)
    context = {
        "devices": devices,
        "total_sensor": total,
        "total_box": total,
        "total_online": online,
        "total_offline": total - online,
        "judul_halaman": "Kelola Sensor",
        "menu_aktif": "kelola_sensor",
    }
    return render(request, "administrasi/kelola_sensor.html", context)


def data_sensor_json(request):
    """Return the latest device and sensor readings for dashboard polling."""
    devices = _get_devices_with_latest_data()
    payload = {
        "devices": [
            {
                "device_id": device.device_id,
                "status_koneksi": device.status_koneksi,
                "weather": (
                    {
                        "temp": device.weather.temp,
                        "rh": device.weather.rh,
                        "lux": device.weather.lux,
                    }
                    if device.weather
                    else None
                ),
                "soil": [
                    {"address": node.address, "adc": node.adc}
                    for node in device.soil
                ],
            }
            for device in devices
        ],
        "summary": {
            "total": len(devices),
            "online": sum(
                device.status_koneksi == Device.STATUS_ONLINE for device in devices
            ),
            "offline": sum(
                device.status_koneksi == Device.STATUS_OFFLINE for device in devices
            ),
        },
    }
    return JsonResponse(payload)
