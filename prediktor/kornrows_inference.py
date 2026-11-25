"""JSON subprocess boundary for Kornrows; no generic models/utils imports here."""
import json
import math
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from django.conf import settings
from PIL import ImageDraw


class ModelUnavailable(RuntimeError):
    pass


def absolute(value):
    path = Path(value)
    return (path if path.is_absolute() else settings.BASE_DIR / path).resolve()


def availability():
    weights = absolute(settings.KORNROWS_WEIGHTS)
    if not weights.is_file():
        return False, 'Model jagung belum tersedia'
    with weights.open('rb') as file:
        if file.read(80).startswith(b'version https://git-lfs.github.com/spec/'):
            return False, 'Model jagung belum tersedia (berkas masih berupa pointer Git LFS)'
    if not absolute(settings.KORNROWS_PYTHON).is_file():
        return False, 'Runtime Kornrows belum tersedia'
    if not (absolute(settings.KORNROWS_REPO) / 'models/experimental.py').is_file():
        return False, 'Kode sumber Kornrows belum tersedia'
    return True, 'Berkas model tersedia; kompatibilitas diperiksa saat deteksi'


def detect(image):
    available, message = availability()
    if not available:
        raise ModelUnavailable(message)
    confidence = settings.KORNROWS_CONFIDENCE
    if not 0 < confidence <= 1 or not 32 <= settings.KORNROWS_IMAGE_SIZE <= 2048:
        raise ValueError('Konfigurasi confidence atau ukuran inferensi Kornrows tidak valid')
    with TemporaryDirectory(prefix='hanjeli-kornrows-') as directory:
        root = Path(directory)
        source = root / 'input.png'
        output = root / 'output.json'
        image.save(source, format='PNG')
        request = {
            'repo': str(absolute(settings.KORNROWS_REPO)),
            'weights': str(absolute(settings.KORNROWS_WEIGHTS)),
            'image': str(source), 'output': str(output),
            'confidence': confidence, 'device': settings.KORNROWS_DEVICE,
            'image_size': settings.KORNROWS_IMAGE_SIZE,
        }
        completed = subprocess.run(
            [str(absolute(settings.KORNROWS_PYTHON)),
             str(settings.BASE_DIR / 'scripts/kornrows_runner.py')],
            input=json.dumps(request), text=True, encoding='utf-8',
            capture_output=True, timeout=settings.KORNROWS_TIMEOUT,
            cwd=directory, shell=False,
        )
        if completed.returncode:
            raise RuntimeError(f'Kornrows exit {completed.returncode}: {completed.stderr[-8000:]}')
        data = json.loads(output.read_text(encoding='utf-8'))
    if data.get('names') != ['cc'] or not isinstance(data.get('detections'), list):
        raise ValueError('Keluaran Kornrows bukan model satu kelas cc')
    if len(data['detections']) > 1000:
        raise ValueError('Terlalu banyak hasil deteksi')
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    detections = []
    width, height = image.size
    for item in data['detections']:
        box, score = item['xyxy'], item['confidence']
        if (item['class_id'] != 0 or len(box) != 4
                or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in [*box, score])
                or not confidence <= score <= 1):
            raise ValueError('Nilai deteksi Kornrows tidak valid')
        x1, y1, x2, y2 = box
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError('Kotak deteksi di luar gambar')
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        draw.rectangle(box, outline='#00dd55', width=3)
        draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill='#ff3333')
        draw.text((x1, max(0, y1 - 12)), f'cc {score:.1%}', fill='#ff3333')
        detections.append({'label': 'cc', 'confidence_percent': score * 100,
                           'xyxy': box, 'center_x': cx, 'center_y': cy})
    return annotated, detections
