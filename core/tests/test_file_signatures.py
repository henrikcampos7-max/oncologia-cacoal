import io
import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.file_security import (
    detect_file_format,
    image_dimensions,
    validate_uploaded_file,
)


class FileSignatureTests(SimpleTestCase):
    def test_pdf_magic_bytes(self):
        arquivo = SimpleUploadedFile("relatorio.pdf", b"%PDF-1.7\nconteudo")
        self.assertEqual(detect_file_format(arquivo.file), "pdf")
        validate_uploaded_file(arquivo, allowed_extensions={".pdf"}, expected_format="pdf")

    def test_pdf_renomeado_para_imagem_e_rejeitado(self):
        arquivo = SimpleUploadedFile("foto.jpg", b"%PDF-1.7\nconteudo")
        with self.assertRaises(ValidationError):
            validate_uploaded_file(arquivo, allowed_extensions={".jpg"}, max_pixels=25_000_000)

    def test_png_magic_bytes_e_dimensao(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (4).to_bytes(4, "big") + (3).to_bytes(4, "big")
        arquivo = SimpleUploadedFile("foto.png", data)
        self.assertEqual(detect_file_format(arquivo.file), "png")
        self.assertEqual(image_dimensions(arquivo.file, "png"), (4, 3))

    def test_imagem_acima_do_limite_de_pixels(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (10_000).to_bytes(4, "big") + (10_000).to_bytes(4, "big")
        arquivo = SimpleUploadedFile("foto.png", data)
        with self.assertRaises(ValidationError):
            validate_uploaded_file(arquivo, allowed_extensions={".png"}, max_pixels=25_000_000)

    def test_sha256_em_streaming_continua_disponivel(self):
        from core.file_security import sha256_stream

        stream = io.BytesIO(b"abc")
        self.assertEqual(sha256_stream(stream), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_symlink_do_storage_continua_bloqueado(self):
        from core.file_security import UnsafeFilePath, safe_real_destination

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "media"
            outside = Path(temp) / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "transferencias").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(UnsafeFilePath):
                safe_real_destination(root, "transferencias/foto.jpg")
