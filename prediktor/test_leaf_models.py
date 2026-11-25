import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from PIL import Image

from . import corn_inference
from .tests import upload


class LeafModelTests(SimpleTestCase):
    url = '/prediktor/jagung/'

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        override = override_settings(MEDIA_ROOT=self.root)
        override.enable()
        self.addCleanup(override.disable)

    def test_choices_and_unknown_model(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'YOLO11 — wjxn13')
        self.assertContains(response, 'HassanCodesIt')
        with patch('prediktor.views.detect') as detect:
            response = self.client.post(self.url, {'model': '../../fake.pt', 'gambar': upload()})
            self.assertIn('model', response.context['form'].errors)
            detect.assert_not_called()

    def test_mock_models_have_distinct_history(self):
        for model_id, folder in [('hassan', 'corn'), ('yolo11', 'corn_leaf_yolo11')]:
            identity = {'id': model_id, 'title': model_id, 'weights_sha256': f'test-{model_id}'}
            with patch('prediktor.views.model_identity', return_value=identity):
                with patch('prediktor.views.detect', return_value=(Image.new('RGB', (32, 24)), [])) as detect:
                    response = self.client.post(self.url, {'model': model_id, 'gambar': upload()})
            self.assertTrue(response.context['has_result'])
            self.assertEqual(detect.call_args.kwargs['model_id'], model_id)
            record = json.loads(next((self.root / folder).rglob('result.json')).read_text())
            self.assertEqual(record['model'], identity)
            self.assertTrue(record['original'].startswith(folder + '/'))
            self.assertIn('created_at', record)
            self.assertContains(response, 'Tidak ada objek yang terdeteksi pada ambang confidence ini')

    def test_yolo11_missing_never_falls_back(self):
        with override_settings(CORN_YOLO11_WEIGHTS=self.root / 'missing.pt'):
            with patch('ultralytics.YOLO') as loader:
                with self.assertLogs('prediktor.views', level='ERROR'):
                    response = self.client.post(self.url, {'model': 'yolo11', 'gambar': upload()})
                loader.assert_not_called()
        self.assertContains(response, 'Deteksi belum dapat dijalankan')
        self.assertFalse(list(self.root.rglob('result.json')))

    def test_yolo11_inference_failure(self):
        with patch('prediktor.views.detect', side_effect=RuntimeError('test private detail')):
            with self.assertLogs('prediktor.views', level='ERROR'):
                response = self.client.post(self.url, {'model': 'yolo11', 'gambar': upload()})
        self.assertContains(response, 'Deteksi belum dapat dijalankan')
        self.assertNotContains(response, 'test private detail')

    def test_mock_loader_cache_and_actual_names(self):
        old = self.root / 'old.pt'
        new = self.root / 'new.pt'
        old.write_bytes(b'test checkpoint old')
        new.write_bytes(b'test checkpoint new')
        models = [Mock(task='detect', names={0: 'old-label'}), Mock(task='detect', names={0: 'new-label'})]
        with override_settings(CORN_YOLO_WEIGHTS=old, CORN_YOLO11_WEIGHTS=new):
            with patch.dict(corn_inference._models, {}, clear=True):
                with patch('ultralytics.YOLO', side_effect=models) as loader:
                    self.assertIs(corn_inference.get_model('hassan'), models[0])
                    self.assertIs(corn_inference.get_model('yolo11'), models[1])
                    self.assertIs(corn_inference.get_model('hassan'), models[0])
                    self.assertIs(corn_inference.get_model('yolo11'), models[1])
                    identity = corn_inference.model_identity('yolo11')
                    self.assertEqual(identity['names'], {0: 'new-label'})
                    self.assertEqual(loader.call_count, 2)

    def test_reject_pointer_and_wrong_task(self):
        path = self.root / 'bad.pt'
        path.write_bytes(b'version https://git-lfs.github.com/spec/v1')
        with override_settings(CORN_YOLO11_WEIGHTS=path):
            with self.assertRaisesRegex(ValueError, 'Git LFS'):
                corn_inference.get_model('yolo11')
            path.write_bytes(b'not a pointer')
            with patch('ultralytics.YOLO', return_value=Mock(task='classify', names={0: 'wrong'})):
                with self.assertRaises(ValueError):
                    corn_inference.get_model('yolo11')

    def test_yolo11_invalid_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        with patch('prediktor.views.detect') as detect:
            response = self.client.post(self.url, {'model': 'yolo11', 'gambar': SimpleUploadedFile('fake.jpg', b'text')})
            self.assertIn('gambar', response.context['form'].errors)
            detect.assert_not_called()
