"""Lazy, process-local YOLO detector. Lock protects the shared predictor."""
import logging
from pathlib import Path
from threading import RLock

from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)
_lock = RLock()
_model = None
_model_path = None


def get_model():
    global _model, _model_path
    path = Path(settings.CORN_YOLO_WEIGHTS)
    if not path.is_absolute():
        path = settings.BASE_DIR / path
    path = path.resolve()
    with _lock:
        if not path.is_file():
            raise FileNotFoundError(f'Bobot jagung tidak ditemukan: {path}')
        if _model is None or _model_path != path:
            from ultralytics import YOLO

            model = YOLO(str(path))
            if model.task != 'detect' or not model.names:
                raise ValueError('Bobot jagung harus berupa model deteksi dengan label kelas.')
            logger.info('Model jagung dimuat: %s task=%s names=%s', path, model.task, model.names)
            _model, _model_path = model, path
        return _model


def detect(image):
    confidence = settings.CORN_YOLO_CONFIDENCE
    if not 0 < confidence <= 1:
        raise ValueError('CORN_YOLO_CONFIDENCE harus lebih dari 0 dan maksimal 1.')
    with _lock:
        model = get_model()
        result = model.predict(
            source=image, conf=confidence, device=settings.CORN_YOLO_DEVICE,
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
