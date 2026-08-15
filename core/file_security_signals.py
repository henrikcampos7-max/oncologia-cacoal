"""Integração dos controles de arquivos com os FileFields sensíveis do core."""

from django.conf import settings
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from .file_security import build_upload_name, validate_uploaded_file
from .models import Transferencia, TransferenciaEvidencia


DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_EXTENSIONS = {".pdf"}


def _max_upload_bytes(kind: str) -> int:
    configured = getattr(settings, "SECURE_UPLOAD_MAX_BYTES", DEFAULT_MAX_UPLOAD_BYTES)
    try:
        return max(1, int(configured))
    except (TypeError, ValueError):
        return DEFAULT_MAX_UPLOAD_BYTES


def _secure_new_upload(field_file, *, prefix: str, extensions: set[str], kind: str) -> None:
    """Valida e troca o nome de um upload novo antes do FileField persistir."""
    if not field_file or field_file._committed:
        return

    validate_uploaded_file(
        field_file.file,
        max_bytes=_max_upload_bytes(kind),
        allowed_extensions=extensions,
    )

    original_name = field_file.name or "arquivo"
    field_file.name = build_upload_name(
        prefix,
        original_name,
        extension_allowlist=extensions,
    )


@receiver(pre_save, sender=Transferencia)
def secure_transferencia_report_upload(sender, instance, **kwargs):
    _secure_new_upload(
        instance.relatorio_arquivo,
        prefix="transferencias/relatorios",
        extensions=PDF_EXTENSIONS,
        kind="relatorio_transferencia",
    )


@receiver(pre_save, sender=TransferenciaEvidencia)
def secure_transferencia_evidence_upload(sender, instance, **kwargs):
    _secure_new_upload(
        instance.arquivo,
        prefix="transferencias/evidencias",
        extensions=IMAGE_EXTENSIONS,
        kind="evidencia_transferencia",
    )
