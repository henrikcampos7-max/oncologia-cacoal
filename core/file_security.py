"""Controles de segurança para arquivos enviados e destinos gerados.

Centraliza contenção de caminhos, rejeição de symlinks, validação de assinatura
real (magic bytes), limites de tamanho/dimensão/páginas e hashes SHA-256.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import struct
from pathlib import Path
from typing import BinaryIO

from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.core.files.uploadedfile import UploadedFile


MAX_FILENAME_LENGTH = 120
DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")
IMAGE_SIGNATURES = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}


class UnsafeFilePath(ValueError):
    """Caminho não permitido pela política de filesystem."""


def is_path_inside(root: str | os.PathLike[str], candidate: str | os.PathLike[str]) -> bool:
    root_path = os.path.realpath(os.path.abspath(os.fspath(root)))
    candidate_path = os.path.realpath(os.path.abspath(os.fspath(candidate)))
    try:
        return os.path.commonpath([root_path, candidate_path]) == root_path
    except ValueError:
        return False


def safe_resolve(root: str | os.PathLike[str], relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise UnsafeFilePath("Caminho relativo vazio ou inválido.")
    if os.path.isabs(relative_path):
        raise UnsafeFilePath("Caminho absoluto não permitido.")
    normalized = relative_path.replace("/", os.sep).replace("\\", os.sep)
    root_path = Path(os.path.abspath(os.fspath(root)))
    candidate = Path(os.path.abspath(os.path.join(root_path, normalized)))
    if not is_path_inside(root_path, candidate):
        raise UnsafeFilePath(f"Caminho fora da raiz autorizada: {relative_path}")
    return candidate


def assert_no_symlink_escape(root: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
    root_path = Path(os.path.abspath(os.fspath(root)))
    target_path = Path(os.path.abspath(os.fspath(target)))
    if not is_path_inside(root_path, target_path):
        raise UnsafeFilePath("Destino fora da raiz autorizada.")
    relative = os.path.relpath(target_path, root_path)
    current = root_path
    if relative == os.curdir:
        return
    for component in Path(relative).parts:
        current /= component
        if current.exists() and current.is_symlink():
            raise UnsafeFilePath(f"Symlink não permitido no caminho: {current}")


def safe_real_destination(root: str | os.PathLike[str], relative_path: str) -> Path:
    candidate = safe_resolve(root, relative_path)
    assert_no_symlink_escape(root, candidate)
    existing = candidate
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    if existing.exists():
        real_existing = Path(os.path.realpath(existing))
        real_root = Path(os.path.realpath(os.path.abspath(os.fspath(root))))
        if not is_path_inside(real_root, real_existing):
            raise UnsafeFilePath("Ancestral real do destino está fora da raiz.")
    return candidate


def sanitize_filename(filename: str, *, max_length: int = MAX_FILENAME_LENGTH) -> str:
    if not isinstance(filename, str):
        raise ValidationError("Nome de arquivo inválido.")
    name = filename.replace("\\", "/").split("/")[-1]
    name = name.strip().replace("\x00", "")
    name = _SAFE_COMPONENT.sub("_", name).strip(" .")
    if not name or name in {".", ".."}:
        raise ValidationError("Nome de arquivo inválido.")
    if len(name) > max_length:
        suffix = Path(name).suffix[:20]
        stem_limit = max(1, max_length - len(suffix) - 9)
        name = f"{Path(name).stem[:stem_limit]}_{secrets.token_hex(4)}{suffix}"
    return name


def build_upload_name(prefix: str, filename: str, *, extension_allowlist: set[str] | None = None) -> str:
    safe_name = sanitize_filename(filename)
    extension = Path(safe_name).suffix.lower()
    if extension_allowlist is not None and extension not in extension_allowlist:
        raise ValidationError(f"Extensão não permitida: {extension or '(sem extensão)'}")
    return f"{prefix.strip('/')}/{secrets.token_hex(16)}{extension}"


def _read_prefix(stream: BinaryIO, size: int = 32) -> bytes:
    position = None
    try:
        if hasattr(stream, "tell"):
            position = stream.tell()
        if hasattr(stream, "seek"):
            stream.seek(0)
        return stream.read(size)
    finally:
        if position is not None and hasattr(stream, "seek"):
            stream.seek(position)


def detect_image_format(stream: BinaryIO) -> str | None:
    header = _read_prefix(stream, 32)
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "webp"
    return None


def detect_file_format(stream: BinaryIO) -> str | None:
    header = _read_prefix(stream, 32)
    if header.startswith(b"%PDF-"):
        return "pdf"
    return detect_image_format(stream)


def image_dimensions(stream: BinaryIO, fmt: str) -> tuple[int, int] | None:
    header = _read_prefix(stream, 64)
    if fmt == "png" and len(header) >= 24:
        return struct.unpack(">II", header[16:24])
    if fmt == "webp" and len(header) >= 30 and header[12:16] == b"VP8X":
        width = 1 + int.from_bytes(header[24:27], "little")
        height = 1 + int.from_bytes(header[27:30], "little")
        return width, height
    if fmt == "jpeg":
        position = None
        try:
            if hasattr(stream, "tell"):
                position = stream.tell()
            if hasattr(stream, "seek"):
                stream.seek(0)
            if stream.read(2) != b"\xff\xd8":
                return None
            while True:
                marker_prefix = stream.read(1)
                if not marker_prefix:
                    return None
                if marker_prefix != b"\xff":
                    continue
                marker = stream.read(1)
                while marker == b"\xff":
                    marker = stream.read(1)
                if marker in {b"\xd8", b"\xd9"}:
                    continue
                length_raw = stream.read(2)
                if len(length_raw) != 2:
                    return None
                length = struct.unpack(">H", length_raw)[0]
                if length < 2:
                    return None
                if marker[0] in set(range(0xC0, 0xC4)) | set(range(0xC5, 0xC8)) | set(range(0xC9, 0xCC)) | set(range(0xCD, 0xD0)):
                    if len(stream.read(1)) != 1:
                        return None
                    size = stream.read(4)
                    if len(size) != 4:
                        return None
                    height, width = struct.unpack(">HH", size)
                    return width, height
                stream.seek(length - 2, os.SEEK_CUR)
        finally:
            if position is not None and hasattr(stream, "seek"):
                stream.seek(position)
    return None


def pdf_page_count(stream: BinaryIO) -> int:
    from pypdf import PdfReader

    position = None
    try:
        if hasattr(stream, "tell"):
            position = stream.tell()
        if hasattr(stream, "seek"):
            stream.seek(0)
        return len(PdfReader(stream).pages)
    except Exception as exc:
        raise ValidationError("PDF inválido ou impossível de analisar com segurança.") from exc
    finally:
        if position is not None and hasattr(stream, "seek"):
            stream.seek(position)


def validate_uploaded_file(
    uploaded: UploadedFile,
    *,
    max_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    allowed_extensions: set[str] | None = None,
    expected_format: str | None = None,
    max_pixels: int | None = None,
    max_pdf_pages: int | None = None,
) -> None:
    if not uploaded:
        raise ValidationError("Arquivo ausente.")
    if uploaded.size is not None and uploaded.size > max_bytes:
        raise ValidationError(f"Arquivo excede o limite de {max_bytes} bytes.")
    safe_name = sanitize_filename(uploaded.name or "arquivo")
    extension = Path(safe_name).suffix.lower()
    if allowed_extensions is not None and extension not in allowed_extensions:
        raise ValidationError(f"Extensão não permitida: {extension or '(sem extensão)'}")
    detected = detect_file_format(uploaded.file)
    if detected is None:
        raise ValidationError("Assinatura do arquivo não reconhecida.")
    if expected_format is not None and detected != expected_format:
        raise ValidationError(f"Conteúdo incompatível: esperado {expected_format}, identificado {detected}.")
    if max_pixels is not None and detected in {"jpeg", "png", "webp"}:
        dimensions = image_dimensions(uploaded.file, detected)
        if dimensions is None:
            raise ValidationError("Dimensões da imagem não puderam ser verificadas com segurança.")
        width, height = dimensions
        if width <= 0 or height <= 0 or width * height > max_pixels:
            raise ValidationError("Imagem excede o limite de resolução permitido.")
    if max_pdf_pages is not None and detected == "pdf" and pdf_page_count(uploaded.file) > max_pdf_pages:
        raise ValidationError(f"PDF excede o limite de {max_pdf_pages} páginas.")


def sha256_stream(stream: BinaryIO, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    position = None
    try:
        if hasattr(stream, "tell"):
            position = stream.tell()
        if hasattr(stream, "seek"):
            stream.seek(0)
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    finally:
        if position is not None and hasattr(stream, "seek"):
            stream.seek(position)
    return digest.hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    with open(path, "rb") as stream:
        return sha256_stream(stream)


def assert_safe_storage_path(root: str | os.PathLike[str], stored_name: str) -> Path:
    try:
        return safe_real_destination(root, stored_name)
    except UnsafeFilePath as exc:
        raise SuspiciousFileOperation(str(exc)) from exc
