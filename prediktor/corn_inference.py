"""Lazy, process-local YOLO detector. Lock protects the shared predictor."""
import logging
import hashlib
from pathlib import Path
from threading import RLock

from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)
_lock = RLock()
_models = {}


def model_configs():
    return {
        'hassan': {'title': 'Model lama — HassanCodesIt', 'weights': settings.CORN_YOLO_WEIGHTS,
                   'confidence': settings.CORN_YOLO_CONFIDENCE, 'device': settings.CORN_YOLO_DEVICE,
                   'source': 'https://github.com/HassanCodesIt/corn-leaf-disease-detection',
                   'commit': 'fe0ef7bce7dbb2890b3374836e9970c841b17219', 'folder': 'corn'},
        'yolo11': {'title': 'YOLO11 — wjxn13', 'weights': settings.CORN_YOLO11_WEIGHTS,
                   'confidence': settings.CORN_YOLO11_CONFIDENCE, 'device': settings.CORN_YOLO11_DEVICE,
                   'source': 'https://github.com/wjxn13/corn-leaf-disease-detector',
                   'commit': 'a662066aa41977c0eb1efd1b278a49a87c300fbe', 'folder': 'corn_leaf_yolo11'},
    }


def get_model(model_id='hassan'):
    config = model_configs()[model_id]
    path = Path(config['weights'])
    if not path.is_absolute():
        path = settings.BASE_DIR / path
    path = path.resolve()
    with _lock:
        if not path.is_file():
            raise FileNotFoundError(f'Bobot jagung tidak ditemukan: {path}')
        stat = path.stat()
        signature = (str(path), stat.st_mtime_ns, stat.st_size)
        if model_id not in _models or _models[model_id]['signature'] != signature:
            from ultralytics import YOLO

            with path.open('rb') as file:
                if file.read(80).startswith(b'version https://git-lfs.github.com/spec/'):
                    raise ValueError('Bobot masih berupa pointer Git LFS')
            model = YOLO(str(path))
            if model.task != 'detect' or not model.names:
                raise ValueError('Bobot jagung harus berupa model deteksi dengan label kelas.')
            logger.info('Model jagung dimuat: %s task=%s names=%s', path, model.task, model.names)
            _models[model_id] = {'model': model, 'signature': signature,
                                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        return _models[model_id]['model']


def model_identity(model_id):
    with _lock:
        model = get_model(model_id)
        config = model_configs()[model_id]
        return {'id': model_id, 'title': config['title'], 'source': config['source'],
                'source_commit': config['commit'], 'weights_sha256': _models[model_id]['sha256'],
                'task': model.task, 'names': model.names,
                'confidence_threshold': config['confidence'], 'device': config['device']}


def detect(image, model_id='hassan'):
    config = model_configs()[model_id]
    confidence = config['confidence']
    if not 0 < confidence <= 1:
        raise ValueError('CORN_YOLO_CONFIDENCE harus lebih dari 0 dan maksimal 1.')
    with _lock:
        model = get_model(model_id)
        result = model.predict(
            source=image, conf=confidence, device=config['device'], imgsz=640,
            save=False, verbose=False,
        )[0]
        detections = []
        for box in result.boxes:
            class_id = int(box.cls.item())
            score = float(box.conf.item())
            detections.append({
                'class_id': class_id, 'label': model.names[class_id],
                'confidence': score, 'confidence_percent': score * 100,
                'xyxy': box.xyxy[0].cpu().tolist(),
            })
        # Ultralytics plot() returns BGR, Pillow expects RGB.
        annotated = Image.fromarray(result.plot()[:, :, ::-1])
        return annotated, detections
