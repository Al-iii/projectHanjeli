
"""View dashboard Modul Administrasi Smart Agriculture."""

from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect

from .models import DataSoil, DataWeather, Device, Pot
from .forms import PotForm

from mqtt_receiver.models import Telemetry

ADC_KERING = 2500
ADC_BASAH = 1200


def klasifikasi_status_tanah(nilai_adc):
    """Klasifikasikan ADC: lebih tinggi berarti tanah lebih kering."""
    if nilai_adc is None or isinstance(nilai_adc, bool):
        return "Tidak Ada Data"
    try:
        nilai_adc = float(nilai_adc)
    except (TypeError, ValueError):
        return "Tidak Ada Data"

    if nilai_adc > ADC_KERING:
        return "Kering"
    if nilai_adc < ADC_BASAH:
        return "Basah"
    return "Normal"


def _klasifikasi_status_perangkat(soil_nodes):
    """Pakai median ADC node valid agar status perangkat mewakili sensornya."""
    nilai_valid = sorted(
        node.adc
        for node in soil_nodes
        if node.adc is not None and isinstance(node.adc, (int, float))
    )
    if not nilai_valid:
        return "Tidak Ada Data"

    tengah = len(nilai_valid) // 2
    if len(nilai_valid) % 2:
        nilai_perwakilan = nilai_valid[tengah]
    else:
        nilai_perwakilan = (nilai_valid[tengah - 1] + nilai_valid[tengah]) / 2
    return klasifikasi_status_tanah(nilai_perwakilan)


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
<<<<<<< HEAD

=======
        device.status_tanah = _klasifikasi_status_perangkat(device.soil)
>>>>>>> c222708b1e020351fdfe2df2a246768cf2099293
    return devices


# ==========================================
# KELOLA SENSOR
# ==========================================

def kelola_sensor(request):
    """Ambil perangkat beserta snapshot weather dan soil terakhirnya."""
    devices = _get_devices_with_latest_data()

    total = len(devices)
    online = sum(
        device.status_koneksi == Device.STATUS_ONLINE
        for device in devices
    )

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
                "status_tanah": device.status_tanah,
            }
            for device in devices
        ],
        "summary": {
            "total": len(devices),
            "online": sum(
                device.status_koneksi == Device.STATUS_ONLINE
                for device in devices
            ),
            "offline": sum(
                device.status_koneksi == Device.STATUS_OFFLINE
                for device in devices
            ),
        },
    }

    return JsonResponse(payload)


# ==========================================
# KELOLA POT
# ==========================================

def pot_list(request):
    """Tampilkan seluruh pot dengan perangkat terkait."""
    pots = Pot.objects.select_related("device_terpasang").all()

    return render(
        request,
        "administrasi/kelola_pot.html",
        {"pots": pots},
    )


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


# ==========================================
# DASHBOARD UTAMA - DATA MQTT
# ==========================================

def dashboard_main(request):
    """Render dashboard utama dengan data telemetry MQTT."""

    telemetry = Telemetry.objects.order_by("-received_at").first()

    history = Telemetry.objects.order_by("-received_at")[:10]

    context = {
        "telemetry": telemetry,
        "history": history,
    }

    return render(request, "dashboard/index.html", context)


# ==========================================
# API DATA TELEMETRY TERBARU
# ==========================================

def telemetry_latest_json(request):
    """Mengirim data telemetry terbaru dalam format JSON."""

    telemetry = Telemetry.objects.order_by("-received_at").first()

    if telemetry is None:
        return JsonResponse({
            "available": False,
            "message": "Belum ada data telemetry.",
        })

    return JsonResponse({
        "available": True,
        "device_id": telemetry.device_id,
        "temperature": telemetry.temperature,
        "air_humidity": telemetry.air_humidity,
        "soil_adc": telemetry.soil_adc,
        "pump": telemetry.pump,
        "valve": telemetry.valve,
        "state": telemetry.state,
        "status": telemetry.status,
        "flow_lpm": telemetry.flow_lpm,
        "received_at": telemetry.received_at.isoformat(),
    })
