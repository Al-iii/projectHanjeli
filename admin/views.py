"""
views.py - View Django untuk modul administrasi "Kelola Sensor".
"""

from django.shortcuts import render

from .models import ControlBox, SensorLingkungan, SoilSensor


def kelola_sensor(request):
    """
    Menampilkan halaman daftar seluruh sensor yang terdaftar di sistem.
    """
    daftar_sensor_lingkungan = SensorLingkungan.objects.select_related("id_box").all()
    daftar_soil_sensor = SoilSensor.objects.select_related("id_box").all()

    daftar_semua_sensor = []

    for sensor in daftar_sensor_lingkungan:
        daftar_semua_sensor.append({
            "id_sensor": f"SL-{sensor.id_sensor:03d}",
            "nama": f"Sensor Lingkungan #{sensor.id_sensor} — {sensor.id_box.nama}",
            "tipe": "Lingkungan",
            "port": sensor.port,
            "status": sensor.id_box.status,
        })

    for soil in daftar_soil_sensor:
        daftar_semua_sensor.append({
            "id_sensor": f"SS-{soil.id_soil:03d}",
            "nama": f"Soil Sensor #{soil.id_soil} — {soil.id_box.nama}",
            "tipe": "Tanah (Soil)",
            "port": soil.port,
            "status": soil.id_box.status,
        })

    total_box    = ControlBox.objects.count()
    total_online = ControlBox.objects.filter(status=ControlBox.STATUS_ONLINE).count()
    total_offline = total_box - total_online  # Hitung di Python, bukan di template

    context = {
        "daftar_sensor": daftar_semua_sensor,
        "total_sensor": len(daftar_semua_sensor),
        "total_box": total_box,
        "total_online": total_online,
        "total_offline": total_offline,          # Kirim langsung ke template
        "judul_halaman": "Kelola Sensor",
        "menu_aktif": "kelola_sensor",
    }

    return render(request, "administrasi/kelola_sensor.html", context)
