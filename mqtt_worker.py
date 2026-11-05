"""
mqtt_worker.py - Worker MQTT untuk Smart Agriculture Hanjeli.

Script ini berjalan sebagai proses terpisah yang mendengarkan data
dari ESP32 Control Box melalui broker MQTT publik, lalu mem-parsing
dan menyimpannya ke database Django melalui Django ORM.

Topik yang di-subscribe:
  - pertanian/sensor/#  : Data pembacaan sensor (suhu, cahaya, soil)
  - pertanian/status/#  : Notifikasi status perangkat (ONLINE/OFFLINE)

Cara menjalankan:
    1. Aktifkan virtual environment: .\\venv\\Scripts\\activate
    2. Pastikan berada di root direktori proyek (setara manage.py)
    3. Jalankan: python mqtt_worker.py

Dependensi:
    pip install paho-mqtt django
"""

import json
import logging
import os
import sys

import paho.mqtt.client as mqtt

# ---------------------------------------------------------------------------
# [LANGKAH 1] Setup Django ORM
#
# Ini WAJIB dilakukan agar kita bisa menggunakan model Django (ORM)
# di luar konteks server Django (runserver). Harus dilakukan SEBELUM
# mengimport model apapun dari Django.
# ---------------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hanjeli.settings")

import django  # noqa: E402

django.setup()

# [LANGKAH 2] Import model SETELAH django.setup() — urutan ini krusial!
from admin.models import ControlBox, SensorLingkungan, SoilSensor  # noqa: E402

# ---------------------------------------------------------------------------
# Konfigurasi Logging — output ke console dengan format timestamp
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mqtt_worker")

# ---------------------------------------------------------------------------
# Konfigurasi MQTT Broker
# ---------------------------------------------------------------------------
BROKER_HOST        = "broker.emqx.io"
BROKER_PORT        = 1883
CLIENT_ID          = "hanjeli-python-worker-001"
TOPIK_DATA_SENSOR  = "pertanian/sensor/#"
TOPIK_STATUS       = "pertanian/status/#"
KEEPALIVE_DETIK    = 60


# ---------------------------------------------------------------------------
# Callback: on_connect
# ---------------------------------------------------------------------------

def on_connect(
    client: mqtt.Client,
    userdata,
    flags,
    reason_code,
    properties,
) -> None:
    """
    Dipanggil otomatis saat klien berhasil / gagal terhubung ke broker.

    Jika berhasil (reason_code == 0), langsung subscribe ke dua topik:
    - pertanian/sensor/#  : payload data sensor dari ESP32
    - pertanian/status/#  : payload notifikasi status perangkat

    Args:
        client      : Instance klien MQTT aktif.
        userdata    : Data konteks opsional.
        flags       : Flag respons broker.
        reason_code : Kode hasil koneksi (0 = sukses).
        properties  : Properti MQTT v5.
    """
    if reason_code == 0:
        logger.info("✓ Terhubung ke broker: %s:%d", BROKER_HOST, BROKER_PORT)
        client.subscribe(TOPIK_DATA_SENSOR)
        client.subscribe(TOPIK_STATUS)
        logger.info("✓ Subscribe ke: %s", TOPIK_DATA_SENSOR)
        logger.info("✓ Subscribe ke: %s", TOPIK_STATUS)
    else:
        logger.error("✗ Gagal terhubung ke broker. Kode: %s", reason_code)


# ---------------------------------------------------------------------------
# Callback: on_disconnect
# ---------------------------------------------------------------------------

def on_disconnect(
    client: mqtt.Client,
    userdata,
    flags,
    reason_code,
    properties,
) -> None:
    """
    Dipanggil otomatis saat klien terputus dari broker.

    Paho-mqtt dengan loop_forever() akan melakukan reconnect otomatis
    jika reason_code bukan 0 (bukan pemutusan disengaja).

    Args:
        client      : Instance klien MQTT aktif.
        userdata    : Data konteks opsional.
        flags       : Flag respons broker.
        reason_code : Kode putus koneksi (0 = disengaja).
        properties  : Properti MQTT v5.
    """
    if reason_code != 0:
        logger.warning(
            "⚠ Koneksi terputus tidak terduga (kode: %s). Reconnect otomatis...",
            reason_code,
        )
    else:
        logger.info("Terputus dari broker secara normal.")


# ---------------------------------------------------------------------------
# Callback: on_message — Titik masuk utama semua pesan MQTT
# ---------------------------------------------------------------------------

def on_message(
    client: mqtt.Client,
    userdata,
    message: mqtt.MQTTMessage,
) -> None:
    """
    Dipanggil setiap kali ada pesan masuk dari topik yang disubscribe.

    Fungsi ini bertindak sebagai router: memeriksa prefix topik dan
    mendelegasikan pemrosesan ke fungsi yang sesuai.

    Format payload JSON (dari ESP32):
    {
        "mac_address"       : "AA:BB:CC:DD:EE:FF",
        "nama"              : "Control Box Kebun 01",
        "lokasi"            : "Kebun Blok A",
        "suhu"              : 28.5,
        "intensitas_cahaya" : 1234.5,
        "kelembaban_titik1" : 65.3,
        "kelembaban_titik2" : 70.1,
        "kelembaban_titik3" : 68.8
    }

    Args:
        client  : Instance klien MQTT aktif.
        userdata: Data konteks opsional.
        message : Objek MQTTMessage (topik + payload).
    """
    topik = message.topic
    logger.info("← Pesan diterima dari topik: [%s]", topik)

    # --- Parse JSON payload ---
    try:
        payload: dict = json.loads(message.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.error("✗ Gagal parse JSON: %s | Error: %s", message.payload, exc)
        return

    # --- Routing berdasarkan prefix topik ---
    if topik.startswith("pertanian/sensor/"):
        _proses_data_sensor(payload)
    elif topik.startswith("pertanian/status/"):
        _proses_notifikasi_status(payload)
    else:
        logger.warning("Topik tidak dikenal: %s", topik)


# ---------------------------------------------------------------------------
# Fungsi Pemroses Data Sensor
# ---------------------------------------------------------------------------

def _proses_data_sensor(payload: dict) -> None:
    """
    Memproses payload data sensor dari ESP32 dan menyimpannya ke database.

    Alur:
    1. Validasi field wajib di payload.
    2. Update/buat ControlBox dan set status → ONLINE.
    3. Update/buat SensorLingkungan dengan data suhu & cahaya.
    4. Update/buat SoilSensor dengan data kelembaban 3 titik.

    Args:
        payload : Dictionary hasil parse JSON dari ESP32.
    """
    mac_address        = payload.get("mac_address")
    nama               = payload.get("nama", f"Box-{mac_address}")
    lokasi             = payload.get("lokasi", "Tidak diketahui")
    suhu               = payload.get("suhu")
    intensitas_cahaya  = payload.get("intensitas_cahaya")
    kelembaban_titik1  = payload.get("kelembaban_titik1")
    kelembaban_titik2  = payload.get("kelembaban_titik2")
    kelembaban_titik3  = payload.get("kelembaban_titik3")

    # Validasi field wajib
    if not mac_address:
        logger.warning("⚠ Payload tidak memiliki 'mac_address'. Pesan diabaikan.")
        return

    # =========================================================
    # [DJANGO ORM] Langkah 1: Update / Buat ControlBox
    #
    # update_or_create:
    #   - Jika ControlBox dengan mac_address ini SUDAH ADA di DB
    #     → update field di 'defaults' (status, nama, lokasi)
    #   - Jika BELUM ADA → buat record baru dengan semua field
    #
    # Ini adalah cara yang direkomendasikan Django untuk operasi
    # "upsert" (update or insert) yang atomic.
    # =========================================================
    try:
        control_box, dibuat_baru = ControlBox.objects.update_or_create(
            mac_address=mac_address,
            defaults={
                "status": ControlBox.STATUS_ONLINE,  # Set ONLINE setiap terima data
                "nama"  : nama,
                "lokasi": lokasi,
            },
        )
        aksi = "Dibuat" if dibuat_baru else "Diperbarui"
        logger.info(
            "✓ ControlBox [%s] %s — status: %s",
            mac_address,
            aksi,
            ControlBox.STATUS_ONLINE,
        )
    except Exception as exc:
        logger.error("✗ Gagal update ControlBox [%s]: %s", mac_address, exc)
        return  # Hentikan jika ControlBox gagal — sensor bergantung padanya

    # =========================================================
    # [DJANGO ORM] Langkah 2: Update / Buat SensorLingkungan
    #
    # Lookup key: kombinasi (id_box + port).
    # Satu port pada satu ControlBox = satu sensor yang sama.
    # Nilai sensor diperbarui setiap pesan baru diterima.
    # =========================================================
    if suhu is not None and intensitas_cahaya is not None:
        try:
            sensor, dibuat = SensorLingkungan.objects.update_or_create(
                id_box=control_box,
                port="I2C/OneWire",   # Port default sensor DHT22 & BH1750 pada ESP32
                defaults={
                    "suhu"              : suhu,
                    "intensitas_cahaya" : intensitas_cahaya,
                },
            )
            aksi = "Dibuat" if dibuat else "Diperbarui"
            logger.info(
                "✓ SensorLingkungan #%d %s — suhu=%.2f°C, cahaya=%.2f lux",
                sensor.id_sensor,
                aksi,
                suhu,
                intensitas_cahaya,
            )
        except Exception as exc:
            logger.error("✗ Gagal update SensorLingkungan: %s", exc)
    else:
        logger.warning("⚠ Data suhu/cahaya tidak tersedia di payload.")

    # =========================================================
    # [DJANGO ORM] Langkah 3: Update / Buat SoilSensor
    # =========================================================
    if None not in (kelembaban_titik1, kelembaban_titik2, kelembaban_titik3):
        try:
            soil, dibuat = SoilSensor.objects.update_or_create(
                id_box=control_box,
                port="ADC-GPIO34/35/32",   # Pin ADC ESP32 untuk 3 soil sensor
                defaults={
                    "kelembaban_titik1": kelembaban_titik1,
                    "kelembaban_titik2": kelembaban_titik2,
                    "kelembaban_titik3": kelembaban_titik3,
                },
            )
            aksi = "Dibuat" if dibuat else "Diperbarui"
            logger.info(
                "✓ SoilSensor #%d %s — titik1=%.1f%%, titik2=%.1f%%, titik3=%.1f%%",
                soil.id_soil,
                aksi,
                kelembaban_titik1,
                kelembaban_titik2,
                kelembaban_titik3,
            )
        except Exception as exc:
            logger.error("✗ Gagal update SoilSensor: %s", exc)
    else:
        logger.warning("⚠ Data kelembaban tidak lengkap di payload.")


def _proses_notifikasi_status(payload: dict) -> None:
    """
    Memproses payload notifikasi status (ONLINE/OFFLINE) dari ESP32.

    Topik pertanian/status/# dikirim oleh ESP32 saat boot (ONLINE)
    atau dapat dikirim sistem lain saat mendeteksi perangkat mati (OFFLINE).

    Args:
        payload : Dictionary hasil parse JSON.
    """
    mac_address = payload.get("mac_address")
    status_baru = payload.get("status", ControlBox.STATUS_OFFLINE)

    if not mac_address:
        logger.warning("⚠ Notifikasi status tanpa 'mac_address'. Diabaikan.")
        return

    # =========================================================
    # [DJANGO ORM] Update kolom status saja tanpa mengubah field lain.
    #
    # update() lebih efisien daripada save() untuk update kolom tunggal
    # karena langsung mengeksekusi satu query UPDATE ke database
    # tanpa perlu membaca record terlebih dahulu.
    #
    # Contoh: ControlBox.objects.filter(mac_address=mac_address)
    #                            .update(status=status_baru)
    # =========================================================
    try:
        jumlah_diupdate = ControlBox.objects.filter(
            mac_address=mac_address
        ).update(status=status_baru)

        if jumlah_diupdate > 0:
            logger.info(
                "✓ Status ControlBox [%s] diperbarui → %s", mac_address, status_baru
            )
        else:
            logger.warning(
                "⚠ ControlBox [%s] tidak ditemukan di database untuk update status.",
                mac_address,
            )
    except Exception as exc:
        logger.error("✗ Gagal update status ControlBox [%s]: %s", mac_address, exc)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def jalankan_worker() -> None:
    """
    Menginisialisasi klien MQTT dan memulai loop tak terbatas.

    Menggunakan MQTT Callback API v2 (paho-mqtt >= 2.0) dan
    loop_forever() yang otomatis menangani reconnect saat koneksi putus.
    """
    logger.info("=" * 55)
    logger.info("   Hanjeli MQTT Worker — Smart Agriculture v1.0   ")
    logger.info("=" * 55)

    klien = mqtt.Client(
        client_id=CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    klien.on_connect    = on_connect
    klien.on_disconnect = on_disconnect
    klien.on_message    = on_message

    try:
        logger.info("Menghubungkan ke %s:%d ...", BROKER_HOST, BROKER_PORT)
        klien.connect(BROKER_HOST, BROKER_PORT, keepalive=KEEPALIVE_DETIK)
        # loop_forever() memblokir thread utama dan menangani reconnect otomatis
        klien.loop_forever()
    except KeyboardInterrupt:
        logger.info("\nWorker dihentikan oleh pengguna (Ctrl+C).")
        klien.disconnect()
        sys.exit(0)
    except Exception as exc:
        logger.critical("Error fatal: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    jalankan_worker()
