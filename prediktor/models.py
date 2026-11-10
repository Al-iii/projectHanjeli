from django.db import models
from django.utils import timezone


class Pot(models.Model):
    nomor = models.PositiveIntegerField(unique=True)

    def __str__(self):
        return f"Pot {self.nomor}"


class Bibit(models.Model):
    pot = models.ForeignKey(
        Pot,
        on_delete=models.CASCADE,
        related_name='daftar_bibit'
    )
    nomor = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['pot', 'nomor'],
                name='unik_nomor_bibit_per_pot'
            )
        ]

    def __str__(self):
        return f"Bibit {self.nomor} - {self.pot}"


class Pengamatan(models.Model):
    bibit = models.ForeignKey(
        Bibit,
        on_delete=models.CASCADE,
        related_name='daftar_pengamatan'
    )
    tanggal = models.DateTimeField(default=timezone.now)
    tinggi_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    foto = models.ImageField(
        upload_to='pengamatan/%Y/%m/%d/',
        blank=True
    )
    catatan = models.TextField(blank=True)

    class Meta:
        ordering = ['-tanggal']

    def __str__(self):
        return f"{self.bibit} - {self.tanggal:%d-%m-%Y}"