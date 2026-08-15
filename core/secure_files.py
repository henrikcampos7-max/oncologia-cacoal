"""Download autenticado para arquivos privados de transferências."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.views.decorators.http import require_GET

from .file_security import UnsafeFilePath, assert_safe_storage_path
from .models import Transferencia, TransferenciaEvidencia


def _clinica_do_usuario(request):
    if request.user.is_superuser:
        return None
    perfil = getattr(request.user, "perfil_oncologia", None)
    if not perfil or not perfil.ativo:
        return False
    return perfil.clinica


def _pode_acessar_transferencia(request, transferencia: Transferencia) -> bool:
    clinica = _clinica_do_usuario(request)
    if clinica is None:
        return bool(request.user.is_superuser)
    if clinica is False:
        return False
    return clinica.pk in {transferencia.clinica_origem_id, transferencia.clinica_destino_id}


def _resposta_arquivo(file_field, *, inline: bool = True):
    if not file_field or not file_field.name:
        raise Http404("Arquivo não encontrado.")
    try:
        path = assert_safe_storage_path(settings.MEDIA_ROOT, file_field.name)
    except Exception as exc:
        raise Http404("Arquivo não disponível.") from exc
    if not path.is_file():
        raise Http404("Arquivo não encontrado.")

    content_type, _ = mimetypes.guess_type(file_field.name)
    response = FileResponse(open(path, "rb"), content_type=content_type or "application/octet-stream")
    disposition = "inline" if inline else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="{Path(file_field.name).name}"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_GET
def baixar_relatorio_transferencia(request, pk: int):
    if not getattr(settings, "SECURE_MEDIA_ENABLED", True):
        return HttpResponse("Arquivos privados desabilitados pela configuração.", status=404)
    transferencia = Transferencia.objects.filter(pk=pk).select_related("clinica_origem", "clinica_destino").first()
    if transferencia is None or not _pode_acessar_transferencia(request, transferencia):
        raise Http404("Arquivo não encontrado.")
    return _resposta_arquivo(transferencia.relatorio_arquivo)


@login_required
@require_GET
def baixar_evidencia_transferencia(request, pk: int):
    if not getattr(settings, "SECURE_MEDIA_ENABLED", True):
        return HttpResponse("Arquivos privados desabilitados pela configuração.", status=404)
    evidencia = (
        TransferenciaEvidencia.objects.filter(pk=pk)
        .select_related("transferencia__clinica_origem", "transferencia__clinica_destino")
        .first()
    )
    if evidencia is None or not _pode_acessar_transferencia(request, evidencia.transferencia):
        raise Http404("Arquivo não encontrado.")
    return _resposta_arquivo(evidencia.arquivo)
