
from django.contrib import admin
from .models import Telemetry


@admin.register(Telemetry)
class TelemetryAdmin(admin.ModelAdmin):
    list_display = (
        'device_id',
        'temperature',
        'air_humidity',
        'soil_adc',
        'valve',
        'pump',
        'received_at',
    )

    list_filter = ('device_id', 'status')
    ordering = ('-received_at',)
