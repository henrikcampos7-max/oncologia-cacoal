from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def health(request):
    """Confirma que a aplicação respondeu; não consulta nem expõe dados."""
    return JsonResponse({"status": "ok", "sistema": "Oncologia Cacoal"})
