from django.core.files.storage import default_storage
from django.shortcuts import render
from PIL import Image, UnidentifiedImageError
import logging
from io import BytesIO
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.views.decorators.http import require_http_methods

from .forms import CornDetectionForm
from .corn_inference import detect

logger = logging.getLogger(__name__)


@require_http_methods(['GET', 'POST'])
def deteksi_jagung(request):
    form = CornDetectionForm(request.POST or None, request.FILES or None)
    context = {'form': form, 'threshold_percent': settings.CORN_YOLO_CONFIDENCE * 100}
    if request.method == 'POST':
        # Bind empty submissions too, so a missing upload gets a field error.
        form = CornDetectionForm(request.POST, request.FILES)
        context['form'] = form
        if form.is_valid():
            saved = []
            try:
                annotated, detections = detect(form.normalized_image)
                token = uuid4().hex
                # Re-encode the validated original, removing metadata and correcting orientation.
                for suffix, image in [('original', form.normalized_image), ('annotated', annotated)]:
                    buffer = BytesIO()
                    image.save(buffer, format='JPEG', quality=95)
                    path = default_storage.save(f'corn/{token}/{suffix}.jpg', ContentFile(buffer.getvalue()))
                    saved.append(path)
                context.update({
                    'original_url': default_storage.url(saved[0]),
                    'annotated_url': default_storage.url(saved[1]),
                    'detections': detections, 'has_result': True,
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
