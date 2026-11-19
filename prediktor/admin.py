from django.contrib import admin
from .models import Pot, Bibit, Pengamatan


@admin.register(Pot)
class PotAdmin(admin.ModelAdmin):
    list_display = ('nomor',)
    ordering = ('nomor',)


@admin.register(Bibit)
class BibitAdmin(admin.ModelAdmin):
    list_display = ('nomor', 'pot')
    list_filter = ('pot',)


@admin.register(Pengamatan)
class PengamatanAdmin(admin.ModelAdmin):
    list_display = ('bibit', 'tanggal', 'tinggi_cm')
    date_hierarchy = 'tanggal'