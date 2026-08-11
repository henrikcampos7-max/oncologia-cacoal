from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import (
    Clinica,
    PerfilUsuario,
    RegistroAuditoria,
    SolicitacaoAcesso,
)


class AcessoFlowTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Clínica Acesso")
        self.admin = get_user_model().objects.create_user(
            username="adminacesso", password="Password123456789!"
        )
        PerfilUsuario.objects.create(
            usuario=self.admin,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.ADMINISTRADOR,
            ativo=True,
        )

    def test_solicitar_acesso_publico_cria_solicitacao(self):
        response = self.client.post(
            reverse("solicitar_acesso"),
            {
                "nome_completo": "Novo Colaborador",
                "email": "novo@exemplo.com",
                "clinica": self.clinica.pk,
                "papel_solicitado": PerfilUsuario.Papel.ENFERMAGEM,
                "justificativa": "Atuação na agenda",
            },
        )
        self.assertEqual(response.status_code, 302)
        solicitacao = SolicitacaoAcesso.objects.get()
        self.assertEqual(solicitacao.status, SolicitacaoAcesso.Status.PENDENTE)
        self.assertEqual(solicitacao.email, "novo@exemplo.com")

    def test_aprovar_solicitacao_cria_usuario_e_perfil(self):
        solicitacao = SolicitacaoAcesso.objects.create(
            nome_completo="Novo Colaborador",
            email="novo@exemplo.com",
            clinica=self.clinica,
            papel_solicitado=PerfilUsuario.Papel.FARMACEUTICO,
        )
        self.client.login(username="adminacesso", password="Password123456789!")
        response = self.client.post(
            reverse("solicitacoes_acesso"),
            {"pk": solicitacao.pk, "acao": "aprovar"},
        )
        self.assertEqual(response.status_code, 302)
        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.status, SolicitacaoAcesso.Status.APROVADA)
        usuario = get_user_model().objects.get(email="novo@exemplo.com")
        perfil = PerfilUsuario.objects.get(usuario=usuario)
        self.assertEqual(perfil.papel, PerfilUsuario.Papel.FARMACEUTICO)
        self.assertEqual(perfil.clinica, self.clinica)
        self.assertTrue(RegistroAuditoria.objects.filter(clinica=self.clinica).exists())

    def test_rejeitar_solicitacao(self):
        solicitacao = SolicitacaoAcesso.objects.create(
            nome_completo="Rejeitada",
            email="rejeitada@exemplo.com",
            clinica=self.clinica,
            papel_solicitado=PerfilUsuario.Papel.LEITURA,
        )
        self.client.login(username="adminacesso", password="Password123456789!")
        response = self.client.post(
            reverse("solicitacoes_acesso"),
            {"pk": solicitacao.pk, "acao": "rejeitar"},
        )
        self.assertEqual(response.status_code, 302)
        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.status, SolicitacaoAcesso.Status.REJEITADA)
        self.assertFalse(
            get_user_model().objects.filter(email="rejeitada@exemplo.com").exists()
        )

    def test_nao_administrador_nao_acessa_aprovacao(self):
        farma = get_user_model().objects.create_user(
            username="farmacesso", password="Password123456789!"
        )
        PerfilUsuario.objects.create(
            usuario=farma, clinica=self.clinica, papel=PerfilUsuario.Papel.FARMACEUTICO, ativo=True
        )
        self.client.login(username="farmacesso", password="Password123456789!")
        response = self.client.get(reverse("solicitacoes_acesso"))
        self.assertEqual(response.status_code, 403)
