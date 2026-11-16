"""MicroPython ESP32 publisher untuk Smart Agriculture."""
import json
import time
import network
from umqtt.simple import MQTTClient

WIFI_SSID = "GANTI_DENGAN_SSID"
WIFI_PASSWORD = "GANTI_DENGAN_PASSWORD"
MQTT_BROKER = "mqtt.sikc.net"
DEVICE_ID = "AGR-MC26-A1B2C3"
STATUS_TOPIC = "agriculture/{}/status".format(DEVICE_ID)
TELEMETRY_TOPIC = "agriculture/{}/telemetry".format(DEVICE_ID)


def connect_wifi():
    """Hubungkan ESP32 ke Wi-Fi."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
    return wlan


def read_dummy_sensor():
    """Buat payload telemetry sesuai kontrak sistem."""
    return {"device_id": DEVICE_ID, "weather": {"temp": 29.4, "rh": 68.2, "lux": 42150}, "soil": {"nodes": [{"adc": 610}, {"adc": 575}, {"adc": 400}]}}


def create_client():
    """Set LWT offline, connect, lalu publish status online."""
    client = MQTTClient(DEVICE_ID, MQTT_BROKER, port=1883, keepalive=60)
    client.set_last_will(STATUS_TOPIC, "offline", retain=True, qos=0)
    client.connect()
    client.publish(STATUS_TOPIC, "online", retain=True, qos=0)
    return client


def main():
    """Publish telemetry setiap lima detik dan tangani koneksi terputus."""
    client = None
    while True:
        try:
            connect_wifi()
            if client is None:
                client = create_client()
            client.publish(TELEMETRY_TOPIC, json.dumps(read_dummy_sensor()))
            time.sleep(5)
        except Exception as exc:
            print("MQTT/Wi-Fi error:", exc)
            client = None
            time.sleep(3)


main()
