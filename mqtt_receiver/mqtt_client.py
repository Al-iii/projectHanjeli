
import os
import json
import django

from paho.mqtt import client as mqtt


# Inisialisasi Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hanjeli.settings')
django.setup()

from django.db import close_old_connections
from .models import Telemetry


# Konfigurasi MQTT
BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'mqtt.sikc.net')
BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
MQTT_TOPIC = os.getenv(
    'MQTT_TOPIC',
    'agriculture/AGR-MC26-513E38/telemetry'
)

USE_TLS = os.getenv('MQTT_USE_TLS', 'false').lower() == 'true'


def to_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def to_int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def get_online_node(payload, section):
    data = payload.get(section) or {}
    nodes = data.get('nodes') or []

    # Prioritaskan sensor yang sedang online
    for node in nodes:
        if node.get('online') is True:
            return node

    # Jika tidak ada yang online, ambil node pertama
    return nodes[0] if nodes else {}


def save_telemetry(payload):
    device_id = payload.get('device_id')

    if not device_id:
        print('Data dilewati: device_id tidak ditemukan.')
        return

    # Mengambil data sensor dari payload
    weather = get_online_node(payload, 'weather')
    soil = get_online_node(payload, 'soil')

    close_old_connections()

    try:
        telemetry = Telemetry.objects.create(
            device_id=device_id,

            temperature=to_float(weather.get('temp')),
            air_humidity=to_float(weather.get('rh')),
            lux=to_float(weather.get('lux')),

            soil_adc=to_int(soil.get('adc')),

            valve=payload.get('valve'),
            pump=payload.get('pump'),
            state=payload.get('state', ''),
            status=payload.get('status', ''),

            flow_lpm=to_float(payload.get('flow_lpm')),
            total_liter=to_float(payload.get('tot_liter')),

            wifi_rssi=to_int(payload.get('wifi_rssi')),
            uptime_s=to_int(payload.get('uptime_s')),

            raw_payload=payload
        )

        print('Data berhasil disimpan ke database!')
        print(f'Device ID: {telemetry.device_id}')
        print(f'Suhu: {telemetry.temperature}')
        print(f'Kelembapan udara: {telemetry.air_humidity}')
        print(f'ADC tanah: {telemetry.soil_adc}')
        print(f'Waktu: {telemetry.received_at}')

    finally:
        close_old_connections()


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print('Berhasil terhubung ke MQTT Broker!')
        client.subscribe(MQTT_TOPIC)
        print(f'Subscribe ke topic: {MQTT_TOPIC}')
    else:
        print(f'Koneksi MQTT gagal: {reason_code}')


def on_message(client, userdata, msg):
    print('\nPesan MQTT diterima!')

    try:
        payload = json.loads(msg.payload.decode('utf-8'))

        print(f'Topic: {msg.topic}')

        save_telemetry(payload)

    except json.JSONDecodeError:
        print('Payload bukan format JSON yang valid.')

    except Exception as error:
        print(f'Gagal memproses data MQTT: {error}')


def start_mqtt_client():
    print('Menghubungkan ke MQTT Broker...')

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    client.on_connect = on_connect
    client.on_message = on_message

    username = os.getenv('MQTT_USERNAME')
    password = os.getenv('MQTT_PASSWORD')

    if username and password:
        client.username_pw_set(username, password)

    if USE_TLS:
        client.tls_set()

    client.connect(
        BROKER_HOST,
        BROKER_PORT,
        keepalive=60
    )

    client.loop_forever()


if __name__ == '__main__':
    start_mqtt_client()
