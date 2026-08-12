from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from core.models import Clinica, RegistroAuditoria
from core.services import registrar_auditoria


class AuditoriaIntegridadeTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Cacoal")
        self.usuario = get_user_model().objects.create_user(
            username="auditoria", password="Password123456789!"
        )

    def test_hash_encadeado_deterministico(self):
        registrar_auditoria(self.clinica, self.usuario, "acao-1", "detalhe-1")
        registrar_auditoria(self.clinica, self.usuario, "acao-2", "detalhe-2")
        registros = list(
            RegistroAuditoria.objects.filter(clinica=self.clinica)
            .order_by("data_hora", "pk")
        )
        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0].hash_anterior, "")
        self.assertEqual(registros[1].hash_anterior, registros[0].hash_registro)
        self.assertEqual(len(registros[0].hash_registro), 64)
        self.assertNotEqual(
            registros[0].hash_registro, registros[1].hash_registro
        )

    def test_integridade_valida(self):
        registrar_auditoria(self.clinica, self.usuario, "acao-1", "detalhe-1")
        registrar_auditoria(self.clinica, self.usuario, "acao-2", "detalhe-2")
        valida, quebrados = RegistroAuditoria.verificar_integridade(self.clinica)
        self.assertTrue(valida)
        self.assertEqual(quebrados, [])

    def test_alteracao_manualmente_detectada(self):
        registrar_auditoria(self.clinica, self.usuario, "acao-1", "detalhe-1")
        registrar_auditoria(self.clinica, self.usuario, "acao-2", "detalhe-2")
        primeiro = RegistroAuditoria.objects.get(acao="acao-1")
        RegistroAuditoria.objects.filter(pk=primeiro.pk).update(acao="acao-ALTERADA")
        valida, quebrados = RegistroAuditoria.verificar_integridade(self.clinica)
        self.assertFalse(valida)
        self.assertEqual(len(quebrados), 1)

    def test_save_de_registro_existente_bloqueado(self):
        registrar_auditoria(self.clinica, self.usuario, "acao-1", "detalhe-1")
        registro = RegistroAuditoria.objects.get(acao="acao-1")
        with self.assertRaises(PermissionDenied):
            registro.detalhes = "tentativa de edição"
            registro.save()

    def test_delete_bloqueado(self):
        registrar_auditoria(self.clinica, self.usuario, "acao-1", "detalhe-1")
        registro = RegistroAuditoria.objects.get(acao="acao-1")
        with self.assertRaises(PermissionDenied):
            registro.delete()

    def test_hashes_diferem_entre_clinicas_mas_nao_quebram(self):
        outra = Clinica.objects.create(nome="Ji-Paraná")
        registrar_auditoria(self.clinica, self.usuario, "mesma-acao", "detalhe")
        registrar_auditoria(outra, self.usuario, "mesma-acao", "detalhe")
        valida_cacoal, _ = RegistroAuditoria.verificar_integridade(self.clinica)
        valida_jp, _ = RegistroAuditoria.verificar_integridade(outra)
        self.assertTrue(valida_cacoal)
        self.assertTrue(valida_jp)

    def test_view_apresenta_integridade(self):
        from django.urls import reverse

        from core.models import PerfilUsuario

        PerfilUsuario.objects.create(
            usuario=self.usuario,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.ADMINISTRADOR,
        )
        registrar_auditoria(self.clinica, self.usuario, "acao-1", "detalhe-1")
        self.client.force_login(self.usuario)
        response = self.client.get(reverse("auditoria"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadeia de integridade válida")

    def test_registros_posteriores_encadeiam_mesmo_com_mesma_order(self):
        registrar_auditoria(self.clinica, self.usuario, "1", "a")
        registrar_auditoria(self.clinica, self.usuario, "2", "b")
        valida, quebrados = RegistroAuditoria.verificar_integridade(self.clinica)
        self.assertTrue(valida, quebrados)