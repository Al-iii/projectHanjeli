import sqlite3
from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase, TransactionTestCase


def locked_error():
    cause = sqlite3.OperationalError('database is locked')
    cause.sqlite_errorcode = sqlite3.SQLITE_BUSY
    error = OperationalError('database is locked')
    error.__cause__ = cause
    return error


class WorkerTransactionTests(TransactionTestCase):
    def test_retry_rolls_back_whole_message_without_duplicate_history(self):
        from admin.models import Device, DataWeather, DataSoil
        from mqtt_receiver.models import Telemetry
        from mqtt_receiver.mqtt_client import save_telemetry
        from mqtt_worker import process_telemetry

        calls = 0

        def fail_after_insert(payload):
            nonlocal calls
            calls += 1
            save_telemetry(payload)
            if calls == 1:
                raise locked_error()

        payload = {'weather': {'nodes': [{'temp': 26, 'rh': 40, 'lux': 10}]},
                   'soil': {'nodes': [{'address': 18, 'adc': 400}]}}
        with patch('mqtt_worker.save_telemetry', side_effect=fail_after_insert):
            with patch('mqtt_receiver.db_retry.time.sleep'):
                process_telemetry('RETRY-TEST', payload)
        self.assertEqual(calls, 2)
        for model in (Device, DataWeather, DataSoil, Telemetry):
            self.assertEqual(model.objects.count(), 1)

    def test_exhausted_retries_leave_no_partial_data(self):
        from admin.models import Device
        from mqtt_worker import process_telemetry
        with patch('mqtt_worker.save_telemetry', side_effect=locked_error()) as save:
            with patch('mqtt_receiver.db_retry.time.sleep'):
                with self.assertRaises(OperationalError):
                    process_telemetry('LOCKED-TEST', {})
        self.assertEqual(save.call_count, 3)
        self.assertFalse(Device.objects.exists())

    def test_unrelated_database_error_is_not_retried(self):
        from mqtt_worker import process_telemetry
        with patch('mqtt_worker.save_telemetry', side_effect=OperationalError('no such table')) as save:
            with self.assertRaises(OperationalError):
                process_telemetry('ERROR-TEST', {})
        self.assertEqual(save.call_count, 1)

    def test_status_retries(self):
        from admin.models import Device
        from mqtt_worker import process_status
        original = Device.objects.update_or_create
        calls = 0

        def fail_once(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise locked_error()
            return original(*args, **kwargs)

        with patch('mqtt_worker.Device.objects.update_or_create', side_effect=fail_once):
            with patch('mqtt_receiver.db_retry.time.sleep'):
                process_status('STATUS-TEST', 'online')
        self.assertEqual(Device.objects.get().status_koneksi, 'online')
        self.assertEqual(calls, 2)

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
