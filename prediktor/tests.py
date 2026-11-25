from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, Client, override_settings
from django.urls import reverse
from PIL import Image

from .corn_inference import get_model
from .forms import CornDetectionForm


def upload(name='leaf.jpg', size=(32, 24), fmt='JPEG', exif=None):
    buffer = BytesIO()
    image = Image.new('RGB', size, 'green')
    image.save(buffer, format=fmt, **({'exif': exif} if exif else {}))
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


class CornUploadTests(SimpleTestCase):
    def test_content_not_extension_and_orientation(self):
        exif = Image.Exif()
        exif[274] = 6
        form = CornDetectionForm(files={'gambar': upload('../../unsafe.exe', exif=exif)})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.normalized_image.size, (24, 32))

    def test_invalid_and_truncated_images(self):
        for data in [b'not an image', upload().read()[:100]]:
            form = CornDetectionForm(files={'gambar': SimpleUploadedFile('fake.jpg', data)})
            self.assertFalse(form.is_valid())

    def test_unsupported_format(self):
        self.assertFalse(CornDetectionForm(files={'gambar': upload(fmt='GIF')}).is_valid())

    @override_settings(CORN_UPLOAD_MAX_BYTES=10)
    def test_file_size(self):
        self.assertFalse(CornDetectionForm(files={'gambar': upload()}).is_valid())

    @override_settings(CORN_UPLOAD_MAX_DIMENSION=20)
    def test_dimension(self):
        self.assertFalse(CornDetectionForm(files={'gambar': upload()}).is_valid())

    @override_settings(CORN_UPLOAD_MAX_PIXELS=100)
    def test_pixel_count(self):
        self.assertFalse(CornDetectionForm(files={'gambar': upload()}).is_valid())

    def test_missing_weights(self):
        with TemporaryDirectory() as directory:
            with override_settings(CORN_YOLO_WEIGHTS=Path(directory) / 'missing.pt'):
                with self.assertRaises(FileNotFoundError):
                    get_model()


class CornPageTests(SimpleTestCase):
    def setUp(self):
        self.url = reverse('prediktor:deteksi_jagung')
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.directory.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        identity = patch('prediktor.views.model_identity', return_value={'id': 'hassan', 'title': 'Model lama — HassanCodesIt'})
        identity.start()
        self.addCleanup(identity.stop)

    def test_get_and_csrf(self):
        self.assertContains(self.client.get(self.url), 'csrfmiddlewaretoken')
        response = Client(enforce_csrf_checks=True).post(self.url, {'gambar': upload()})
        self.assertEqual(response.status_code, 403)

    @patch('prediktor.views.detect')
    def test_invalid_upload_does_not_run_model(self, detect):
        self.client.post(self.url, {'gambar': SimpleUploadedFile('fake.jpg', b'hello')})
        detect.assert_not_called()
        response = self.client.post(self.url)
        self.assertTrue(response.context['form'].errors)

    @patch('prediktor.views.detect')
    def test_success_unique_files_and_labels(self, detect):
        detect.return_value = (Image.new('RGB', (32, 24)), [
            {'label': 'corn_rust', 'confidence_percent': 82.5},
        ])
        for _ in range(2):
            response = self.client.post(self.url, {'gambar': upload()})
            self.assertContains(response, 'corn_rust')
            self.assertContains(response, '82.50%')
            self.assertContains(response, 'Jumlah deteksi: 1')
            for key in ('original_url', 'annotated_url'):
                path = Path(self.directory.name) / response.context[key].removeprefix('/media/')
                with Image.open(path) as image:
                    image.verify()
        self.assertEqual(len(list(Path(self.directory.name).rglob('*.jpg'))), 4)

    @patch('prediktor.views.detect')
    def test_no_detection(self, detect):
        detect.return_value = (Image.new('RGB', (32, 24)), [])
        response = self.client.post(self.url, {'gambar': upload()})
        self.assertContains(response, 'Tidak ada objek yang terdeteksi pada ambang confidence ini')
        self.assertNotContains(response, 'tanaman sehat')

    def test_missing_weights_friendly_error_and_log(self):
        with override_settings(CORN_YOLO_WEIGHTS=Path(self.directory.name) / 'missing.pt'):
            with self.assertLogs('prediktor.views', level='ERROR'):
                response = self.client.post(self.url, {'gambar': upload()})
        self.assertContains(response, 'Deteksi belum dapat dijalankan')
        self.assertFalse(list(Path(self.directory.name).rglob('*.jpg')))

    @patch('prediktor.views.detect')
    def test_partial_storage_failure_cleans_up(self, detect):
        from django.core.files.storage import default_storage
        actual_save = default_storage.save
        calls = 0

        def fail_second(name, content):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('disk full')
            return actual_save(name, content)

        detect.return_value = (Image.new('RGB', (32, 24)), [])
        with patch('prediktor.views.default_storage.save', side_effect=fail_second):
            with self.assertLogs('prediktor.views', level='ERROR'):
                response = self.client.post(self.url, {'gambar': upload()})
        self.assertContains(response, 'Deteksi belum dapat dijalankan')
        self.assertEqual(calls, 2)
        self.assertFalse(list(Path(self.directory.name).rglob('*.jpg')))
