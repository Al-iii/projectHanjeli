import json
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.urls import resolve, reverse

from mqtt_receiver.models import Telemetry

from .models import DataSoil, DataWeather, Device, LogPenyiraman, Pot
from .views import klasifikasi_status_tanah

# Create your tests here.


class SoilClassificationTests(SimpleTestCase):
    def test_thresholds_and_missing_values(self):
        cases = [
            (0, "Basah"), (1199, "Basah"), (1200, "Normal"),
            (2500, "Normal"), (2501, "Kering"), (None, "Tidak Ada Data"),
            (True, "Tidak Ada Data"), (-1, "Tidak Ada Data"),
            ("invalid", "Tidak Ada Data"), (float("nan"), "Tidak Ada Data"),
        ]
        for adc, expected in cases:
            with self.subTest(adc=adc):
                self.assertEqual(klasifikasi_status_tanah(adc), expected)


class SensorMonitoringTests(TestCase):
    def setUp(self):
        self.device = Device.objects.create(device_id="TEST-SENSOR", status_koneksi="online")
        self.pot = Pot.objects.create(
            kode_pot="POT-TEST", jenis_tanaman="Hanjeli", tanggal_tanam="2026-11-24",
            fase_pertumbuhan="Bibit", device_terpasang=self.device,
        )

    def reading(self, **kwargs):
        fields = {
            "device_id": self.device.pk, "temperature": 25.2,
            "air_humidity": 61.1, "soil_adc": 386,
            "pump": False, "valve": False,
        }
        fields.update(kwargs)
        return Telemetry.objects.create(**fields)

    def test_routes_sidebar_and_empty_states(self):
        self.assertEqual(reverse("dashboard_main"), "/admin")
        self.assertEqual(reverse("administrasi:kelola_sensor"), "/admin/sensor/")
        self.assertEqual(reverse("administrasi:data_sensor_json"), "/admin/sensor/data/")
        self.assertEqual(reverse("administrasi:pot_list"), "/admin/sensor/pot/")
        self.assertEqual(reverse("admin:index"), "/django-admin/")
        self.assertEqual(resolve("/admin").func.__module__, "dashboard.views")
        for url in ("/admin", "/admin/", "/admin/sensor/", "/admin/sensor/data/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get("/admin"), 'href="/admin/sensor/"')
        page = self.client.get("/admin/sensor/")
        self.assertContains(page, 'href="/admin"')
        self.assertContains(page, 'data-json-url="/admin/sensor/data/"')
        self.assertContains(page, "Belum ada riwayat pembacaan sensor.")
        self.assertContains(page, "Belum ada log penyiraman.")

    def test_history_is_latest_twenty_and_polling_never_writes(self):
        DataWeather.objects.create(device=self.device, temp=25.2, rh=61.1, lux=0)
        DataSoil.objects.create(device=self.device, address=18, adc=386)
        for adc in range(21):
            self.reading(soil_adc=adc)
        response = self.client.get(reverse("administrasi:data_sensor_json"))
        data = response.json()
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertEqual(len(data["sensor_history"]), 20)
        self.assertEqual(data["sensor_history"][0]["adc"], 20)
        self.assertEqual(data["sensor_history"][-1]["adc"], 1)
        self.assertEqual(data["sensor_history"][0]["pots"], [self.pot.pk])
        self.assertEqual(data["sensor_history"][0]["status_tanah"], "Basah")
        self.assertEqual(data["devices"][0]["soil"], [{"address": 18, "adc": 386}])
        self.assertEqual(data["summary"]["online"], 1)
        self.assertEqual(len(data["irrigation_logs"]), 1)
        self.client.get(reverse("administrasi:data_sensor_json"))
        self.assertEqual(Telemetry.objects.count(), 21)
        self.assertEqual(LogPenyiraman.objects.count(), 1)
        self.assertContains(self.client.get("/admin/sensor/"), "POT-TEST")

    def test_log_records_transitions_and_explicit_trigger_without_duplicates(self):
        self.reading()
        self.reading()
        self.reading(pump=True, raw_payload={"trigger": "manual"})
        self.reading(pump=True, raw_payload={"trigger": "manual"})
        self.reading(pump=True, valve=True, raw_payload={"trigger": "manual"})
        self.reading(pump=True, valve=True, raw_payload={"trigger": "dry_soil"})
        self.reading(raw_payload={"trigger": "dry_soil"})
        logs = list(LogPenyiraman.objects.order_by("waktu", "pk"))
        self.assertEqual([log.status for log in logs], ["OFF", "ON", "ON", "ON", "OFF"])
        self.assertEqual(logs[0].keterangan, "Status awal teramati")
        self.assertEqual(logs[1].pemicu, "Manual")
        self.assertEqual(logs[3].pemicu, "Otomatis (Tanah Kering)")
        self.assertEqual(logs[0].kode_pot, [self.pot.pk])

    def test_dry_soil_does_not_invent_watering_or_a_trigger(self):
        self.reading(soil_adc=3000)
        self.reading(soil_adc=3500)
        log = LogPenyiraman.objects.get()
        self.assertEqual(log.status, "OFF")
        self.assertEqual(log.pemicu, "Tidak dilaporkan perangkat")

    def test_unknown_state_and_other_devices_do_not_affect_transitions(self):
        self.reading(pump=None, valve=None)
        self.reading(pump=True, valve=None)
        self.assertFalse(LogPenyiraman.objects.exists())
        first = self.reading()
        self.reading(device_id="TEST-SECOND", pump=True, valve=True)
        self.reading()
        self.assertEqual(LogPenyiraman.objects.count(), 2)
        first.temperature = 26
        first.save()
        self.assertEqual(LogPenyiraman.objects.count(), 2)

    def test_log_keeps_identity_after_pot_device_and_telemetry_removal(self):
        reading = self.reading()
        self.pot.delete()
        self.device.delete()
        reading.delete()
        log = LogPenyiraman.objects.get()
        self.assertIsNone(log.device)
        self.assertIsNone(log.telemetry)
        self.assertEqual(log.identitas_perangkat, "TEST-SENSOR")
        self.assertEqual(log.kode_pot, ["POT-TEST"])

    def test_existing_pot_crud_at_new_urls(self):
        data = {
            "kode_pot": "POT-NEW", "jenis_tanaman": "Hanjeli",
            "tanggal_tanam": "2026-11-24", "fase_pertumbuhan": "Bibit",
            "device_terpasang": self.device.pk, "keterangan": "",
        }
        response = self.client.post(reverse("administrasi:pot_create"), data)
        self.assertRedirects(response, "/admin/sensor/pot/")
        edit_url = reverse("administrasi:pot_update", args=["POT-NEW"])
        self.assertEqual(self.client.get(edit_url).status_code, 200)
        data["fase_pertumbuhan"] = "Vegetatif"
        self.assertRedirects(self.client.post(edit_url, data), "/admin/sensor/pot/")
        self.assertEqual(Pot.objects.get(pk="POT-NEW").fase_pertumbuhan, "Vegetatif")
        delete_url = reverse("administrasi:pot_delete", args=["POT-NEW"])
        self.assertEqual(self.client.get(delete_url).status_code, 200)
        self.assertTrue(Pot.objects.filter(pk="POT-NEW").exists())
        self.assertRedirects(self.client.post(delete_url), "/admin/sensor/pot/")
        self.assertFalse(Pot.objects.filter(pk="POT-NEW").exists())


class WorkerHistoryIntegrationTests(TransactionTestCase):
    def test_real_payload_shape_saves_snapshots_history_and_transitions(self):
        # Jalankan callback lokal, tanpa koneksi/publish ke broker produksi.
        from mqtt_worker import on_message

        payload = {
            "device_id": "TEST-WORKER", "pump": False, "valve": False,
            "state": "idle", "status": "ok",
            "weather": {"nodes": [
                {"address": 1, "online": True, "temp": 25.2, "rh": 61.1, "lux": 0},
            ]},
            "soil": {"nodes": [
                {"address": 19, "online": False},
                {"address": 18, "online": True, "adc": 386},
            ]},
        }

        def deliver(suffix, body):
            on_message(None, None, SimpleNamespace(
                topic=f"agriculture/TEST-WORKER/{suffix}", payload=body,
            ))

        deliver("telemetry", json.dumps(payload).encode())
        deliver("telemetry", json.dumps(payload).encode())
        self.assertEqual(DataWeather.objects.count(), 1)
        self.assertEqual(DataSoil.objects.count(), 1)
        self.assertEqual(DataSoil.objects.get().adc, 386)
        self.assertEqual(Telemetry.objects.count(), 2)
        self.assertEqual(LogPenyiraman.objects.count(), 1)
        payload["pump"] = True
        deliver("telemetry", json.dumps(payload).encode())
        self.assertEqual(LogPenyiraman.objects.count(), 2)
        self.assertEqual(LogPenyiraman.objects.first().status, "ON")
        deliver("status", b"offline")
        self.assertEqual(Device.objects.get(pk="TEST-WORKER").status_koneksi, "offline")
        deliver("config", b"ignored")
        self.assertEqual(Telemetry.objects.count(), 3)
