from django.http import JsonResponse


def health(request):
    return JsonResponse({"service": "accounting", "status": "ok"})
