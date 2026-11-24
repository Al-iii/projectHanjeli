import warnings

from django import forms
from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError


class CornDetectionForm(forms.Form):
    gambar = forms.FileField(
        label='Foto daun jagung',
        widget=forms.ClearableFileInput(attrs={
            'accept': 'image/jpeg,image/png,image/webp', 'class': 'form-control',
        }),
    )

    def clean_gambar(self):
        upload = self.cleaned_data['gambar']
        if upload.size > settings.CORN_UPLOAD_MAX_BYTES:
            raise forms.ValidationError('Ukuran file maksimal 10 MB.')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(upload) as source:
                    if source.format not in {'JPEG', 'PNG', 'WEBP'}:
                        raise forms.ValidationError('Gunakan gambar JPEG, PNG, atau WebP.')
                    width, height = source.size
                    if (max(width, height) > settings.CORN_UPLOAD_MAX_DIMENSION
                            or width * height > settings.CORN_UPLOAD_MAX_PIXELS):
                        raise forms.ValidationError('Gambar maksimal 6000 piksel per sisi dan 20 megapiksel.')
                    if getattr(source, 'n_frames', 1) != 1:
                        raise forms.ValidationError('Gunakan gambar diam, bukan animasi.')
                    source.verify()
                upload.seek(0)
                with Image.open(upload) as source:
                    source.load()
                    self.normalized_image = ImageOps.exif_transpose(source).convert('RGB')
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
                Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise forms.ValidationError('File rusak atau tidak terbaca sebagai gambar yang aman.') from exc
        finally:
            upload.seek(0)
        return upload
