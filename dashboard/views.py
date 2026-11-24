
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from mqtt_receiver.models import Telemetry


def index(request):
    telemetry = Telemetry.objects.order_by('-received_at').first()
    history = Telemetry.objects.order_by('-received_at')[:10]

    context = {
        'telemetry': telemetry,
        'history': history,
    }

    return render(request, 'dashboard/index.html', context)


def latest_telemetry(request):
    telemetry = Telemetry.objects.order_by('-received_at').first()
    history = Telemetry.objects.order_by('-received_at')[:10]

    if not telemetry:
        return JsonResponse({
            'available': False,
            'history': [],
        })

    def serialize(item):
        return {
            'device_id': item.device_id,
            'temperature': item.temperature,
            'air_humidity': item.air_humidity,
            'soil_adc': item.soil_adc,
            'pump': item.pump,
            'valve': item.valve,
            'state': item.state,
            'status': item.status,
            'flow_lpm': item.flow_lpm,
            'received_at': timezone.localtime(
                item.received_at
            ).strftime('%d/%m/%Y %H:%M:%S'),
        }

    return JsonResponse({
        'available': True,
        'telemetry': serialize(telemetry),
        'history': [serialize(item) for item in history],
    })
