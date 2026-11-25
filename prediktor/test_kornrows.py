"""Boundary tests use mock detections, never substitutes for a real checkpoint."""
from io import BytesIO
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, override_settings
from PIL import Image

from . import kornrows_inference as service
from .forms import KornrowsDetectionForm


def upload(data=None):
    if data is None:
        buffer = BytesIO()
        Image.new('RGB', (40, 30), 'green').save(buffer, format='PNG')
        data = buffer.getvalue()
    return SimpleUploadedFile('unsafe.exe', data, content_type='text/plain')


class KornrowsTests(SimpleTestCase):
    url = '/prediktor/tanaman-jagung/'

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.override = override_settings(MEDIA_ROOT=self.root / 'media',
                                           KORNROWS_WEIGHTS=self.root / 'missing.pt')
        self.override.enable()
        self.addCleanup(self.override.disable)

    def test_actual_missing_model_and_no_outputs(self):
        self.assertContains(self.client.get(self.url), 'Model jagung belum tersedia')
        with patch('prediktor.kornrows_inference.subprocess.run') as run:
            with self.assertLogs('prediktor.views', level='WARNING'):
                response = self.client.post(self.url, {'gambar': upload()})
            run.assert_not_called()
        self.assertContains(response, 'Model jagung belum tersedia')
        self.assertNotContains(response, 'Jumlah objek terdeteksi:')
        self.assertFalse((self.root / 'media').exists())

    def test_lfs_pointer_is_not_a_model(self):
        path = self.root / 'pointer.pt'
        path.write_text('version https://git-lfs.github.com/spec/v1\noid sha256:fake')
        with override_settings(KORNROWS_WEIGHTS=path):
            self.assertFalse(service.availability()[0])

    def test_invalid_upload_and_missing_field(self):
        with patch('prediktor.views.kornrows_inference.detect') as detect:
            for data in ({'gambar': upload(b'not an image')}, {}):
                response = self.client.post(self.url, data)
                self.assertTrue(response.context['form'].errors)
            detect.assert_not_called()

    def test_size_dimensions_orientation(self):
        with override_settings(CORN_UPLOAD_MAX_BYTES=5):
            self.assertFalse(KornrowsDetectionForm(files={'gambar': upload()}).is_valid())
        with override_settings(CORN_UPLOAD_MAX_DIMENSION=10):
            self.assertFalse(KornrowsDetectionForm(files={'gambar': upload()}).is_valid())
        with override_settings(CORN_UPLOAD_MAX_PIXELS=10):
            self.assertFalse(KornrowsDetectionForm(files={'gambar': upload()}).is_valid())
        from .tests import upload as oriented_upload
        exif = Image.Exif()
        exif[274] = 6
        form = KornrowsDetectionForm(files={'gambar': oriented_upload(exif=exif)})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.normalized_image.size, (24, 32))

    def test_csrf_and_leaf_page_preserved(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post(self.url, {'gambar': upload()}).status_code, 403)
        self.assertContains(self.client.get('/prediktor/jagung/'), 'Deteksi Penyakit Daun Jagung')

    @patch('prediktor.views.kornrows_inference.detect')
    def test_mock_success_unique_storage(self, detect):
        detect.return_value = (Image.new('RGB', (40, 30)), [
            {'label': 'cc', 'confidence_percent': 90, 'center_x': 20, 'center_y': 15},
        ])
        for _ in range(2):
            response = self.client.post(self.url, {'gambar': upload()})
            self.assertContains(response, 'Jumlah objek terdeteksi: 1')
            self.assertContains(response, '90.00%')
        files = list((self.root / 'media').rglob('*.jpg'))
        self.assertEqual(len(files), 4)
        for path in files:
            with Image.open(path) as image:
                image.verify()

    @patch('prediktor.views.kornrows_inference.detect')
    def test_mock_empty(self, detect):
        detect.return_value = (Image.new('RGB', (40, 30)), [])
        self.assertContains(self.client.post(self.url, {'gambar': upload()}),
                            'Tidak ada objek yang terdeteksi pada ambang confidence ini')

    @patch('prediktor.views.kornrows_inference.detect', side_effect=RuntimeError('incompatible checkpoint'))
    def test_failure_logged(self, detect):
        with self.assertLogs('prediktor.views', level='ERROR'):
            response = self.client.post(self.url, {'gambar': upload()})
        self.assertContains(response, 'Deteksi gagal')
        self.assertNotContains(response, 'incompatible checkpoint')
        self.assertFalse((self.root / 'media').exists())

    def test_partial_save_is_cleaned_up(self):
        from django.core.files.storage import default_storage
        save = default_storage.save
        count = 0

        def fail_second(name, content):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('disk full')
            return save(name, content)

        with patch('prediktor.views.kornrows_inference.detect', return_value=(Image.new('RGB', (40, 30)), [])):
            with patch('prediktor.views.default_storage.save', side_effect=fail_second):
                with self.assertLogs('prediktor.views', level='ERROR'):
                    self.client.post(self.url, {'gambar': upload()})
        self.assertFalse(list(self.root.rglob('*.jpg')))

    @patch('prediktor.kornrows_inference.availability', return_value=(True, 'mock ready'))
    def test_adapter_json_and_center(self, available):
        def fake_process(command, **kwargs):
            self.assertFalse(kwargs['shell'])
            self.assertEqual(kwargs['timeout'], 120)
            request = json.loads(kwargs['input'])
            self.assertTrue(Path(request['image']).is_absolute())
            Path(request['output']).write_text(json.dumps({'names': ['cc'], 'detections': [
                {'class_id': 0, 'xyxy': [2, 4, 20, 24], 'confidence': 0.8},
            ]}))
            return subprocess.CompletedProcess(command, 0, '', '')

        before = Path.cwd()
        with patch('prediktor.kornrows_inference.subprocess.run', side_effect=fake_process):
            annotated, detections = service.detect(Image.new('RGB', (40, 30)))
        self.assertEqual(Path.cwd(), before)
        self.assertEqual((detections[0]['center_x'], detections[0]['center_y']), (11, 14))
        self.assertEqual(annotated.getpixel((11, 14)), (255, 51, 51))

    @patch('prediktor.kornrows_inference.availability', return_value=(True, 'mock ready'))
    def test_timeout_nonzero_and_malformed_output(self, available):
        with patch('prediktor.kornrows_inference.subprocess.run', side_effect=subprocess.TimeoutExpired('worker', 120)):
            with self.assertRaises(subprocess.TimeoutExpired):
                service.detect(Image.new('RGB', (40, 30)))
        with patch('prediktor.kornrows_inference.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'load failed')):
            with self.assertRaisesRegex(RuntimeError, 'load failed'):
                service.detect(Image.new('RGB', (40, 30)))

        def fake_output(command, **kwargs):
            request = json.loads(kwargs['input'])
            Path(request['output']).write_text('{"names": ["person"], "detections": []}')
            return subprocess.CompletedProcess(command, 0, '', '')

        with patch('prediktor.kornrows_inference.subprocess.run', side_effect=fake_output):
            with self.assertRaises(ValueError):
                service.detect(Image.new('RGB', (40, 30)))
