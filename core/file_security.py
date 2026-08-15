"""Controles de segurança para arquivos enviados e destinos gerados.

Este módulo centraliza regras de filesystem para evitar path traversal,
symlinks fora da raiz autorizada e nomes de arquivo controlados pelo usuário.
Ele não substitui a autorização de negócio: o chamador continua responsável
por decidir se o arquivo/artefato pode ser aceito.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
from pathlib import Path
from typing import BinaryIO

from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.core.files.uploadedfile import UploadedFile


MAX_FILENAME_LENGTH = 120
DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")


class UnsafeFilePath(ValueError):
    """Caminho não permitido pela política de filesystem."""


def is_path_inside(root: str | os.PathLike[str], candidate: str | os.PathLike[str]) -> bool:
    """Retorna True somente se candidate estiver dentro de root.

    A comparação usa caminhos absolutos normalizados e ``os.path.commonpath``;
    não usa ``startswith``, evitando falsos positivos como /media e /media-old.
    """
    root_path = os.path.realpath(os.path.abspath(os.fspath(root)))
    candidate_path = os.path.realpath(os.path.abspath(os.fspath(candidate)))
    try:
        return os.path.commonpath([root_path, candidate_path]) == root_path
    except ValueError:
        # Em Windows, volumes diferentes não compartilham uma raiz comum.
        return False


def safe_resolve(root: str | os.PathLike[str], relative_path: str) -> Path:
    """Resolve um caminho relativo e impede escape da raiz autorizada."""
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise UnsafeFilePath("Caminho relativo vazio ou inválido.")

    if os.path.isabs(relative_path):
        raise UnsafeFilePath("Caminho absoluto não permitido.")

    # Aceita somente separadores relativos; convertemos barras para o SO atual.
    normalized = relative_path.replace("/", os.sep).replace("\\", os.sep)
    root_path = Path(os.path.abspath(os.fspath(root)))
    candidate = Path(os.path.abspath(os.path.join(root_path, normalized)))

    if not is_path_inside(root_path, candidate):
        raise UnsafeFilePath(f"Caminho fora da raiz autorizada: {relative_path}")

    return candidate


def assert_no_symlink_escape(root: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
    """Rejeita symlinks existentes no caminho entre root e target.

    Isso evita que um diretório aparentemente permitido redirecione a escrita
    para /etc, outro volume ou qualquer local fora da raiz.
    """
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
    """Retorna destino seguro, considerando componentes existentes e symlinks."""
    candidate = safe_resolve(root, relative_path)
    assert_no_symlink_escape(root, candidate)

    # Se o destino ainda não existe, o último ancestral existente é verificado.
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
    """Gera nome seguro sem preservar caminhos enviados pelo cliente."""
    if not isinstance(filename, str):
        raise ValidationError("Nome de arquivo inválido.")

    # Nunca confiar em basename de um SO diferente: normalizamos ambos os estilos.
    name = filename.replace("\\", "/").split("/")[-1]
    name = name.strip().replace("\x00", "")
    name = _SAFE_COMPONENT.sub("_", name)
    name = name.strip(" .")

    if not name or name in {".", ".."}:
        raise ValidationError("Nome de arquivo inválido.")

    if len(name) > max_length:
        suffix = Path(name).suffix[:20]
        stem_limit = max(1, max_length - len(suffix) - 9)
        name = f"{Path(name).stem[:stem_limit]}_{secrets.token_hex(4)}{suffix}"

    return name


def build_upload_name(prefix: str, filename: str, *, extension_allowlist: set[str] | None = None) -> str:
    """Cria um nome de upload sem reutilizar o nome fornecido pelo usuário como ID."""
    safe_name = sanitize_filename(filename)
    extension = Path(safe_name).suffix.lower()

    if extension_allowlist is not None and extension not in extension_allowlist:
        raise ValidationError(f"Extensão não permitida: {extension or '(sem extensão)'}")

    token = secrets.token_hex(16)
    return f"{prefix.strip('/')}/{token}{extension}"


def validate_uploaded_file(
    uploaded: UploadedFile,
    *,
    max_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    allowed_extensions: set[str] | None = None,
) -> None:
    """Valida limites básicos antes de persistir um upload."""
    if not uploaded:
        raise ValidationError("Arquivo ausente.")

    if uploaded.size is not None and uploaded.size > max_bytes:
        raise ValidationError(f"Arquivo excede o limite de {max_bytes} bytes.")

    # O nome é validado separadamente porque content-type/extensão não são
    # mecanismos suficientes para autenticar o formato do conteúdo.
    safe_name = sanitize_filename(uploaded.name or "arquivo")
    extension = Path(safe_name).suffix.lower()
    if allowed_extensions is not None and extension not in allowed_extensions:
        raise ValidationError(f"Extensão não permitida: {extension or '(sem extensão)'}")


def sha256_stream(stream: BinaryIO, *, chunk_size: int = 1024 * 1024) -> str:
    """Calcula SHA-256 em streaming sem carregar o arquivo inteiro na memória."""
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
    """Calcula SHA-256 de arquivo local em streaming."""
    with open(path, "rb") as stream:
        return sha256_stream(stream)


def assert_safe_storage_path(root: str | os.PathLike[str], stored_name: str) -> Path:
    """Valida um nome já retornado por uma Storage antes de uso no filesystem."""
    try:
        path = safe_real_destination(root, stored_name)
    except UnsafeFilePath as exc:
        raise SuspiciousFileOperation(str(exc)) from exc
    return path
