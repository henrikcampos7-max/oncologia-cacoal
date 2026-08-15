import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.models import Clinica, PerfilUsuario, Transferencia, TransferenciaEvidencia


class SecureFilesTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.media.cleanup)

        self.origem = Clinica.objects.create(nome="Origem")
        self.destino = Clinica.objects.create(nome="Destino")
        self.outro = Clinica.objects.create(nome="Outra")
        User = get_user_model()
        self.user = User.objects.create_user(username="farmaceutico", password="senha-segura-123456")
        PerfilUsuario.objects.create(
            usuario=self.user,
            clinica=self.destino,
            papel=PerfilUsuario.Papel.FARMACEUTICO,
            ativo=True,
        )
        self.transferencia = Transferencia.objects.create(
            clinica_origem=self.origem,
            clinica_destino=self.destino,
            numero="TR-SEC-0001",
        )

    def test_anonimo_nao_acessa_arquivo_privado(self):
        response = self.client.get(f"/transferencias/{self.transferencia.pk}/relatorio/arquivo/")
        self.assertEqual(response.status_code, 302)

    def test_usuario_de_outra_clinica_nao_acessa_transferencia(self):
        PerfilUsuario.objects.filter(usuario=self.user).update(clinica=self.outro)
        self.client.force_login(self.user)
        response = self.client.get(f"/transferencias/{self.transferencia.pk}/relatorio/arquivo/")
        self.assertEqual(response.status_code, 404)

    def test_usuario_da_clinica_recebe_404_sem_arquivo(self):
        self.client.force_login(self.user)
        response = self.client.get(f"/transferencias/{self.transferencia.pk}/relatorio/arquivo/")
        self.assertEqual(response.status_code, 404)

    def test_evidencia_nao_expoe_url_sem_arquivo(self):
        evidencia = TransferenciaEvidencia(
            transferencia=self.transferencia,
            hash_arquivo="a" * 64,
        )
        self.assertFalse(bool(evidencia.arquivo.name))
