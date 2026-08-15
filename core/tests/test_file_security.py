import os
import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.file_security import (
    UnsafeFilePath,
    build_upload_name,
    is_path_inside,
    safe_real_destination,
    safe_resolve,
    sanitize_filename,
    sha256_stream,
    validate_uploaded_file,
)


class FileSecurityTests(SimpleTestCase):
    def test_path_inside_nao_confunde_prefixo(self):
        self.assertTrue(is_path_inside("/tmp/media", "/tmp/media/foto.jpg"))
        self.assertFalse(is_path_inside("/tmp/media", "/tmp/media-old/foto.jpg"))

    def test_rejeita_caminho_absoluto(self):
        with self.assertRaises(UnsafeFilePath):
            safe_resolve("/tmp/media", "/etc/passwd")

    def test_rejeita_escape_da_raiz(self):
        with self.assertRaises(UnsafeFilePath):
            safe_resolve("/tmp/media", "../../etc/passwd")

    def test_permite_subdiretorio(self):
        result = safe_resolve("/tmp/media", "transferencias/evidencias/arquivo.jpg")
        self.assertEqual(
            result,
            Path("/tmp/media/transferencias/evidencias/arquivo.jpg"),
        )

    def test_symlink_nao_pode_redirecionar_destino(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "media"
            outside = Path(temp) / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "evidencias").symlink_to(outside, target_is_directory=True)

            with self.assertRaises(UnsafeFilePath):
                safe_real_destination(root, "evidencias/foto.jpg")

    def test_sanitiza_nome_sem_preservar_caminho(self):
        self.assertEqual(sanitize_filename("../../segredo.txt"), "segredo.txt")
        self.assertNotIn("/", sanitize_filename("pasta/arquivo.pdf"))
        self.assertNotIn("\\", sanitize_filename(r"pasta\arquivo.pdf"))

    def test_build_upload_name_gera_id_aleatorio(self):
        nome = build_upload_name(
            "transferencias/evidencias",
            "foto original.JPG",
            extension_allowlist={".jpg", ".jpeg", ".png"},
        )
        partes = nome.split("/")
        self.assertEqual(partes[0:2], ["transferencias", "evidencias"])
        self.assertTrue(partes[-1].endswith(".jpg"))
        self.assertNotEqual(partes[-1], "foto original.JPG")

    def test_extensao_nao_permitida(self):
        with self.assertRaises(ValidationError):
            build_upload_name(
                "transferencias/evidencias",
                "arquivo.exe",
                extension_allowlist={".jpg", ".png"},
            )

    def test_limite_de_upload(self):
        arquivo = SimpleUploadedFile("foto.jpg", b"123456")
        with self.assertRaises(ValidationError):
            validate_uploaded_file(arquivo, max_bytes=5)

    def test_sha256_stream_nao_altera_posicao(self):
        from io import BytesIO

        stream = BytesIO(b"abc")
        stream.seek(1)
        digest = sha256_stream(stream)
        self.assertEqual(stream.tell(), 1)
        self.assertEqual(
            digest,
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )
