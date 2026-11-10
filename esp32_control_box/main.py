"""MicroPython firmware ESP32 untuk Smart Agriculture."""

import json
import time

import network
from umqtt.simple import MQTTClient


# Ganti nilai Wi-Fi sebelum mengunggah file ke ESP32.
WIFI_SSID = "GANTI_DENGAN_SSID"
WIFI_PASSWORD = "GANTI_DENGAN_PASSWORD"

MQTT_BROKER = "mqtt.sikc.net"
MQTT_PORT = 1883
DEVICE_ID = "AGR-MC26-A1B2C3"
STATUS_TOPIC = "agriculture/{}/status".format(DEVICE_ID)
TELEMETRY_TOPIC = "agriculture/{}/telemetry".format(DEVICE_ID)


def connect_wifi():
    """Menghubungkan ESP32 ke Wi-Fi dan menunggu sampai siap."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Menghubungkan ke Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)

    print("Wi-Fi terhubung:", wlan.ifconfig()[0])
    return wlan


def read_dummy_sensors():
    """Menghasilkan pembacaan dummy sesuai format telemetry sistem."""
    return {
        "device_id": DEVICE_ID,
        "weather": {
            "temp": 29.4,
            "rh": 68.2,
            "lux": 42150,
        },
        "soil": {
            "nodes": [
                {"adc": 610},
                {"adc": 575},
                {"adc": 400},
            ]
        },
    }


def create_mqtt_client():
    """Membuat koneksi MQTT dengan Last Will offline."""
    client = MQTTClient(
        client_id=DEVICE_ID,
        server=MQTT_BROKER,
        port=MQTT_PORT,
        keepalive=60,
    )
    client.set_last_will(STATUS_TOPIC, "offline", retain=True, qos=0)
    client.connect()
    client.publish(STATUS_TOPIC, "online", retain=True, qos=0)
    print("MQTT terhubung dan status online dikirim")
    return client


def main():
    """Loop utama untuk publish telemetry setiap lima detik."""
    client = None

    while True:
        try:
            connect_wifi()

            if client is None:
                client = create_mqtt_client()

            payload = json.dumps(read_dummy_sensors())
            client.publish(TELEMETRY_TOPIC, payload)
            print("Telemetry terkirim:", payload)
            time.sleep(5)

        except Exception as error:
            print("Koneksi atau publish gagal:", error)
            client = None
            time.sleep(3)


main()
