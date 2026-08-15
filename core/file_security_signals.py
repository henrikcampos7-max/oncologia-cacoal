"""Integração dos controles de arquivos com os FileFields sensíveis do core."""

from django.conf import settings
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .file_security import build_upload_name, validate_uploaded_file
from .models import Transferencia, TransferenciaEvidencia

DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_EXTENSIONS = {".pdf"}


def _max_upload_bytes() -> int:
    configured = getattr(settings, "SECURE_UPLOAD_MAX_BYTES", DEFAULT_MAX_UPLOAD_BYTES)
    try:
        return max(1, int(configured))
    except (TypeError, ValueError):
        return DEFAULT_MAX_UPLOAD_BYTES


def _secure_new_upload(field_file, *, prefix: str, extensions: set[str], expected_format: str | None = None, max_pixels: int | None = None, max_pdf_pages: int | None = None) -> None:
    if not field_file or field_file._committed:
        return
    validate_uploaded_file(
        field_file,
        max_bytes=_max_upload_bytes(),
        allowed_extensions=extensions,
        expected_format=expected_format,
        max_pixels=max_pixels,
        max_pdf_pages=max_pdf_pages,
    )
    field_file.name = build_upload_name(prefix, field_file.name or "arquivo", extension_allowlist=extensions)


@receiver(pre_save, sender=Transferencia)
def secure_transferencia_report_upload(sender, instance, **kwargs):
    _secure_new_upload(
        instance.relatorio_arquivo,
        prefix="transferencias/relatorios",
        extensions=PDF_EXTENSIONS,
        expected_format="pdf",
        max_pdf_pages=getattr(settings, "SECURE_PDF_MAX_PAGES", 100),
    )


@receiver(pre_save, sender=TransferenciaEvidencia)
def secure_transferencia_evidence_upload(sender, instance, **kwargs):
    _secure_new_upload(
        instance.arquivo,
        prefix="transferencias/evidencias",
        extensions=IMAGE_EXTENSIONS,
        max_pixels=getattr(settings, "SECURE_IMAGE_MAX_PIXELS", 25_000_000),
    )
