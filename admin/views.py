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


# CRUD Pot ditambahkan terpisah agar view sensor dan endpoint MQTT tetap utuh.
from django.shortcuts import get_object_or_404, redirect  # noqa: E402

from .forms import PotForm  # noqa: E402
from .models import Pot  # noqa: E402


def pot_list(request):
    """Tampilkan seluruh pot dengan perangkat terkait."""
    pots = Pot.objects.select_related("device_terpasang").all()
    return render(request, "administrasi/kelola_pot.html", {"pots": pots})


def pot_create(request):
    """Buat pot baru dari form yang valid."""
    form = PotForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("administrasi:pot_list")
    return render(
        request,
        "administrasi/pot_form.html",
        {"form": form, "judul": "Tambah Pot"},
    )


def pot_update(request, kode_pot):
    """Edit data pot berdasarkan primary key kode_pot."""
    pot = get_object_or_404(Pot, pk=kode_pot)
    form = PotForm(
        request.POST if request.method == "POST" else None,
        instance=pot,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("administrasi:pot_list")
    return render(
        request,
        "administrasi/pot_form.html",
        {"form": form, "judul": "Edit Pot", "pot": pot},
    )


def pot_delete(request, kode_pot):
    """Hapus pot hanya setelah konfirmasi dikirim dengan POST."""
    pot = get_object_or_404(Pot, pk=kode_pot)
    if request.method == "POST":
        pot.delete()
        return redirect("administrasi:pot_list")
    return render(
        request,
        "administrasi/pot_confirm_delete.html",
        {"pot": pot},
    )


def dashboard_main(request):
    """Render landing page utama Smart Agriculture."""
    return render(request, "administrasi/dashboard.html")
