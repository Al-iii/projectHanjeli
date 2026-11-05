from django.core.files.storage import default_storage
from django.shortcuts import render
from PIL import Image, UnidentifiedImageError


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