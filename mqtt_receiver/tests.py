from django.test import TestCase

class WorkerDashboardTests(TestCase):
    def test_worker_saves_dashboard_history_and_admin_snapshot(self):
        from admin.models import DataWeather
        from mqtt_receiver.models import Telemetry
        from mqtt_worker import process_telemetry

        payload = {
            'weather': {'nodes': [
                {'online': True, 'temp': 26.4, 'rh': 43.7, 'lux': 0},
            ]},
            'soil': {'nodes': [{'online': True, 'address': 18, 'adc': 408}]},
            'pump': False,
            'valve': False,
        }
        process_telemetry('TEST-DEVICE', payload)
        self.assertEqual(DataWeather.objects.get().temp, 26.4)
        self.assertEqual(Telemetry.objects.get().device_id, 'TEST-DEVICE')
        data = self.client.get('/api/telemetry/latest/').json()
        self.assertTrue(data['available'])
        self.assertEqual(data['telemetry']['temperature'], 26.4)
        self.assertEqual(data['telemetry']['soil_adc'], 408)
        self.assertContains(self.client.get('/'), 'TEST-DEVICE')
        process_telemetry('TEST-DEVICE', payload)
        self.assertEqual(Telemetry.objects.count(), 2)
        self.assertEqual(DataWeather.objects.count(), 1)
