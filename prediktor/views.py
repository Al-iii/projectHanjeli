from django.core.files.storage import default_storage
from django.shortcuts import render
from PIL import Image, UnidentifiedImageError
import logging
import json
from io import BytesIO
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .forms import LeafDiseaseDetectionForm, KornrowsDetectionForm
from .corn_inference import detect, model_configs, model_identity
from . import kornrows_inference

logger = logging.getLogger(__name__)


@require_http_methods(['GET', 'POST'])
def deteksi_tanaman_jagung(request):
    form = KornrowsDetectionForm(request.POST, request.FILES) if request.method == 'POST' else KornrowsDetectionForm()
    available, status = kornrows_inference.availability()
    context = {'form': form, 'model_available': available, 'model_status': status,
               'threshold_percent': settings.KORNROWS_CONFIDENCE * 100}
    if request.method == 'POST' and form.is_valid():
        saved = []
        try:
            annotated, detections = kornrows_inference.detect(form.normalized_image)
            token = uuid4().hex
            for suffix, image in [('original', form.normalized_image), ('annotated', annotated)]:
                buffer = BytesIO()
                image.save(buffer, format='JPEG', quality=95)
                saved.append(default_storage.save(f'kornrows/{token}/{suffix}.jpg', ContentFile(buffer.getvalue())))
            context.update({'has_result': True, 'detections': detections,
                            'original_url': default_storage.url(saved[0]),
                            'annotated_url': default_storage.url(saved[1])})
        except kornrows_inference.ModelUnavailable as exc:
            logger.warning('Kornrows tidak tersedia: %s (weights=%s)', exc, settings.KORNROWS_WEIGHTS)
            context['error'] = str(exc)
        except Exception:
            logger.exception('Inferensi Kornrows gagal')
            for path in saved:
                try:
                    default_storage.delete(path)
                except Exception:
                    logger.exception('Gagal membersihkan berkas Kornrows %s', path)
            context['error'] = ('Deteksi gagal atau melewati batas waktu. Periksa checkpoint dan runtime Kornrows. '
                                'Detail kesalahan dicatat di log server.')
    return render(request, 'prediktor/kornrows.html', context)


@require_http_methods(['GET', 'POST'])
def deteksi_jagung(request):
    form = LeafDiseaseDetectionForm(request.POST or None, request.FILES or None)
    context = {'form': form, 'threshold_percent': settings.CORN_YOLO_CONFIDENCE * 100}
    if request.method == 'POST':
        # Bind empty submissions too, so a missing upload gets a field error.
        form = LeafDiseaseDetectionForm(request.POST, request.FILES)
        context['form'] = form
        if form.is_valid():
            saved = []
            try:
                model_id = form.cleaned_data['model']
                config = model_configs()[model_id]
                context['threshold_percent'] = config['confidence'] * 100
                annotated, detections = detect(form.normalized_image, model_id=model_id)
                identity = model_identity(model_id)
                token = uuid4().hex
                # Re-encode the validated original, removing metadata and correcting orientation.
                for suffix, image in [('original', form.normalized_image), ('annotated', annotated)]:
                    buffer = BytesIO()
                    image.save(buffer, format='JPEG', quality=95)
                    path = default_storage.save(f"{config['folder']}/{token}/{suffix}.jpg", ContentFile(buffer.getvalue()))
                    saved.append(path)
                record = {'created_at': timezone.now().isoformat(), 'model': identity,
                          'original': saved[0], 'annotated': saved[1], 'detections': detections}
                saved.append(default_storage.save(f"{config['folder']}/{token}/result.json",
                             ContentFile(json.dumps(record, ensure_ascii=False, indent=2).encode('utf-8'))))
                context.update({
                    'original_url': default_storage.url(saved[0]),
                    'annotated_url': default_storage.url(saved[1]),
                    'detections': detections, 'has_result': True,
                    'model_identity': identity, 'record_url': default_storage.url(saved[2]),
                })
            except Exception:
                logger.exception('Deteksi jagung gagal')
                for path in saved:
                    try:
                        default_storage.delete(path)
                    except Exception:
                        logger.exception('Gagal membersihkan berkas deteksi %s', path)
                context['error'] = ('Deteksi belum dapat dijalankan. Pastikan bobot model tersedia '
                                    'dan konfigurasi benar, lalu coba lagi. Detail tersimpan di log server.')
    return render(request, 'prediktor/jagung.html', context)


def beranda(request):
    context = {}

    if request.method == 'POST':
        gambar = request.FILES.get('gambar')

        if not gambar:
            context['error'] = 'Pilih gambar terlebih dahulu.'
        else:
            try:
                # Pastikan file yang dikirim benar-benar gambar
                Image.open(gambar).verify()
                gambar.seek(0)

                # Simpan ke media/prediktor/
                path_gambar = default_storage.save(
                    f'prediktor/{gambar.name}',
                    gambar
                )
                context['gambar_url'] = default_storage.url(path_gambar)

            except (UnidentifiedImageError, OSError):
                context['error'] = 'File tidak terbaca sebagai gambar.'

    return render(request, 'prediktor/beranda.html', context)
