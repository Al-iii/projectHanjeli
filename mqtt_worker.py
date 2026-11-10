"""Worker Paho MQTT yang menyimpan payload ESP32 ke Django ORM."""

import json
import logging
import os

import django
import paho.mqtt.client as mqtt

# Django harus diinisialisasi sebelum model di-import.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hanjeli.settings")
django.setup()

from admin.models import DataSoil, DataWeather, Device  # noqa: E402

BROKER_HOST = "mqtt.sikc.net"
BROKER_PORT = 1883
CLIENT_ID = "hanjeli-django-worker"
STATUS_TOPIC = "agriculture/+/status"
TELEMETRY_TOPIC = "agriculture/+/telemetry"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mqtt_worker")


def on_connect(client, userdata, flags, reason_code, properties=None):
    """Subscribe ulang setelah koneksi atau reconnect berhasil."""
    if reason_code == 0:
        client.subscribe([(STATUS_TOPIC, 0), (TELEMETRY_TOPIC, 0)])
        logger.info("Connected to %s:%s", BROKER_HOST, BROKER_PORT)
    else:
        logger.error("MQTT connection failed: %s", reason_code)


def on_message(client, userdata, message):
    """Route status string atau telemetry JSON berdasarkan topiknya."""
    parts = message.topic.split("/")
    if len(parts) != 3 or parts[0] != "agriculture":
        return

    device_id, message_type = parts[1], parts[2]
    try:
        raw_payload = message.payload.decode("utf-8")
        payload = json.loads(raw_payload) if message_type == "telemetry" else raw_payload.strip().lower()
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Payload invalid dari %s: %s", message.topic, exc)
        return

    try:
        if message_type == "status":
            process_status(device_id, payload)
        elif message_type == "telemetry":
            process_telemetry(device_id, payload)
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Data dari %s tidak valid: %s", device_id, exc)


def process_status(device_id, status):
    """Upsert Device dari payload LWT online/offline."""
    if status not in (Device.STATUS_ONLINE, Device.STATUS_OFFLINE):
        raise ValueError("status harus online atau offline")
    Device.objects.update_or_create(
        device_id=device_id,
        defaults={"status_koneksi": status},
    )


def process_telemetry(topic_device_id, payload):
    """Simpan weather dan node soil terbaru dari telemetry ESP32."""
    if payload.get("device_id") != topic_device_id:
        raise ValueError("device_id payload berbeda dengan device_id topic")

    device, _ = Device.objects.update_or_create(
        device_id=topic_device_id,
        defaults={"status_koneksi": Device.STATUS_ONLINE},
    )

    weather_nodes = payload.get("weather", {}).get("nodes", [])
    for node in weather_nodes:
        if node.get("online") is False:
            continue
        DataWeather.objects.update_or_create(
            device=device,
            defaults={
                "temp": node.get("temp"),
                "rh": node.get("rh"),
                "lux": node.get("lux"),
            },
        )
        break

    soil_nodes = payload.get("soil", {}).get("nodes", [])
    for node in soil_nodes:
        if "address" not in node:
            continue
        DataSoil.objects.update_or_create(
            device=device,
            address=int(node["address"]),
            defaults={"adc": node.get("adc")},
        )

    logger.info("Telemetry tersimpan untuk %s", topic_device_id)


def main():
    """Jalankan worker MQTT dengan reconnect otomatis."""
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
