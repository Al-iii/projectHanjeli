"""Subscriber MQTT yang menyimpan telemetry asli ke Django ORM."""

import json
import logging
import os
import uuid

import django
import paho.mqtt.client as mqtt

# Siapkan Django sebelum mengimpor model agar worker mandiri dapat memakai ORM.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hanjeli.settings")
django.setup()

from admin.models import DataSoil, DataWeather, Device  # noqa: E402
from mqtt_receiver.mqtt_client import save_telemetry  # noqa: E402
from mqtt_receiver.db_retry import atomic_message  # noqa: E402
from django.db import connections, transaction  # noqa: E402

BROKER_HOST = "mqtt.sikc.net"
BROKER_PORT = 1883
CLIENT_ID = os.getenv("MQTT_CLIENT_ID") or f"hanjeli-worker-{uuid.uuid4().hex[:12]}"
DEVICE_TOPIC = "agriculture/#"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("mqtt_worker")


def on_connect(client, userdata, flags, reason_code, properties=None):
    """Subscribe ke seluruh topik perangkat setiap koneksi berhasil."""
    if reason_code == 0:
        client.subscribe(DEVICE_TOPIC, qos=0)
        logger.info("Terhubung ke %s:%s; subscribe %s", BROKER_HOST, BROKER_PORT, DEVICE_TOPIC)
    else:
        logger.error("Koneksi MQTT gagal: %s", reason_code)


def on_message(client, userdata, message):
    """Route pesan berdasarkan suffix topik dan abaikan topic non-data."""
    parts = message.topic.split("/")
    if len(parts) < 3 or parts[0] != "agriculture":
        return

    # Topic kontrol/config bukan sumber data sensor yang disimpan worker.
    if message.topic.endswith(("/config", "/control/state")):
        logger.debug("Topic diabaikan: %s", message.topic)
        return

    device_id = parts[1]
    try:
        if message.topic.endswith("/status"):
            status = message.payload.decode("utf-8").strip().lower()
            process_status(device_id, status)
        elif message.topic.endswith("/telemetry"):
            payload = json.loads(message.payload.decode("utf-8"))
            process_telemetry(device_id, payload)
        else:
            logger.debug("Suffix topic tidak ditangani: %s", message.topic)
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logger.warning("Pesan invalid pada %s: %s", message.topic, exc)
    except Exception:
        # Catat kegagalan ORM/koneksi DB tanpa menghentikan loop MQTT.
        logger.exception("Gagal memproses pesan pada %s", message.topic)


@atomic_message
def process_status(device_id, status):
    """Simpan status LWT plain text; payload status bukan JSON."""
    if status not in (Device.STATUS_ONLINE, Device.STATUS_OFFLINE):
        raise ValueError("Status harus 'online' atau 'offline'.")

    Device.objects.update_or_create(
        device_id=device_id,
        defaults={"status_koneksi": status},
    )
    transaction.on_commit(lambda: logger.info("Status %s = %s", device_id, status))


@atomic_message
def process_telemetry(topic_device_id, payload):
    """Upsert Device, satu node cuaca, dan semua node tanah ber-ADC."""
    if not isinstance(payload, dict):
        raise TypeError("Payload telemetry harus berupa object JSON.")

    device_id = payload.get("device_id") or topic_device_id
    if device_id != topic_device_id:
        raise ValueError("device_id payload berbeda dari device_id topic.")

    device, _ = Device.objects.update_or_create(
        device_id=device_id,
        defaults={"status_koneksi": Device.STATUS_ONLINE},
    )

    # DataWeather hanya punya satu baris per perangkat, jadi simpan node
    # cuaca online pertama yang memiliki seluruh field model.
    weather = payload.get("weather") or {}
    weather_nodes = weather.get("nodes", []) if isinstance(weather, dict) else []
    for node in weather_nodes:
        if not isinstance(node, dict) or node.get("online") is False:
            continue
        if not all(key in node and node[key] is not None for key in ("temp", "rh", "lux")):
            continue
        DataWeather.objects.update_or_create(
            device=device,
            defaults={
                "temp": float(node["temp"]),
                "rh": float(node["rh"]),
                "lux": float(node["lux"]),
            },
        )
        break

    # Node soil offline biasanya tidak punya ADC; abaikan sampai ADC valid
    # tersedia, supaya nilai pengukuran terakhir tetap tersimpan.
    soil = payload.get("soil") or {}
    soil_nodes = soil.get("nodes", []) if isinstance(soil, dict) else []
    for node in soil_nodes:
        if not isinstance(node, dict) or "address" not in node or "adc" not in node:
            continue
        if node["address"] is None or node["adc"] is None:
            continue
        address = int(node["address"])
        adc = int(node["adc"])
        if address <= 0 or adc < 0:
            continue
        DataSoil.objects.update_or_create(
            device=device,
            address=address,
            defaults={"adc": adc},
        )

    # Administrasi memakai snapshot; dashboard memakai riwayat Telemetry.
    save_telemetry({**payload, "device_id": device_id})
    transaction.on_commit(lambda: logger.info("Telemetry tersimpan untuk %s", device_id))


def main():
    """Jalankan subscriber dengan reconnect otomatis Paho."""
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Worker dihentikan oleh pengguna.")
    finally:
        client.disconnect()
        connections.close_all()


if __name__ == "__main__":
    main()
