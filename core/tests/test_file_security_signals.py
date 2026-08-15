import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from core.models import Clinica, Transferencia, TransferenciaEvidencia


class SecureUploadSignalsTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.media.cleanup)

        self.origem = Clinica.objects.create(nome="Origem")
        self.destino = Clinica.objects.create(nome="Destino")
        self.transferencia = Transferencia.objects.create(
            clinica_origem=self.origem,
            clinica_destino=self.destino,
            numero="TR-2026-0001",
        )

    def test_evidencia_recebe_nome_interno_aleatorio(self):
        evidencia = TransferenciaEvidencia(
            transferencia=self.transferencia,
            arquivo=SimpleUploadedFile(
                "../../foto original.jpg",
                b"imagem de teste",
                content_type="image/jpeg",
            ),
            hash_arquivo="a" * 64,
        )
        evidencia.save()

        self.assertTrue(evidencia.arquivo.name.startswith("transferencias/evidencias/"))
        self.assertNotIn("foto original", evidencia.arquivo.name)
        self.assertTrue(evidencia.arquivo.name.endswith(".jpg"))
        self.assertTrue(Path(evidencia.arquivo.path).is_file())

    def test_evidencia_rejeita_extensao_nao_permitida(self):
        evidencia = TransferenciaEvidencia(
            transferencia=self.transferencia,
            arquivo=SimpleUploadedFile(
                "arquivo.exe",
                b"conteudo",
                content_type="application/octet-stream",
            ),
            hash_arquivo="b" * 64,
        )
        with self.assertRaises(ValidationError):
            evidencia.save()

    def test_relatorio_recebe_nome_interno_pdf(self):
        self.transferencia.relatorio_arquivo = SimpleUploadedFile(
            "../../relatorio.pdf",
            b"%PDF-1.4 teste",
            content_type="application/pdf",
        )
        self.transferencia.save()

        self.assertTrue(self.transferencia.relatorio_arquivo.name.startswith("transferencias/relatorios/"))
        self.assertNotIn("relatorio", self.transferencia.relatorio_arquivo.name)
        self.assertTrue(self.transferencia.relatorio_arquivo.name.endswith(".pdf"))
        self.assertTrue(Path(self.transferencia.relatorio_arquivo.path).is_file())
