from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Apresentacao,
    Clinica,
    Lote,
    Medicamento,
    MovimentacaoEstoque,
    Paciente,
    PerfilUsuario,
    Protocolo,
    SessaoTratamento,
)


class SessaoFaltasTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Clínica Relatórios")
        self.user = get_user_model().objects.create_user(
            username="adminrel", password="Password123456789!"
        )
        PerfilUsuario.objects.create(
            usuario=self.user,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.ADMINISTRADOR,
            ativo=True,
        )
        self.client.login(username="adminrel", password="Password123456789!")
        self.protocolo = Protocolo.objects.create(clinica=self.clinica, nome="Protocolo Faltas")
        self.paciente = Paciente.objects.create(
            clinica=self.clinica,
            nome="Paciente Faltas",
            diagnostico="Teste",
            data_inicio=timezone.localdate(),
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=Medicamento.objects.create(
                clinica=self.clinica, nome="Med Faltas", principio_ativo="Ativo"
            ),
            concentracao="1 mg/mL",
            descricao="Frasco 10 mg",
            quantidade_mg=Decimal("10"),
        )
        self.lote = Lote.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            numero_lote="LOT-FALTA",
            data_validade=timezone.localdate() + timedelta(days=150),
            quantidade_inicial=10,
            quantidade_atual=10,
        )

    def criar_sessao(self, horas=1):
        return SessaoTratamento.objects.create(
            clinica=self.clinica,
            paciente=self.paciente,
            protocolo=self.protocolo,
            data_hora=timezone.now() + timedelta(hours=horas),
        )

    def test_marcar_falta_registra_status_e_motivo(self):
        sessao = self.criar_sessao()
        response = self.client.post(
            reverse("atualizar_status_sessao", args=[sessao.pk]),
            {"status": "faltou", "motivo": "Paciente não compareceu"},
        )
        self.assertEqual(response.status_code, 302)
        sessao.refresh_from_db()
        self.assertEqual(sessao.status, SessaoTratamento.Status.FALTOU)
        self.assertEqual(sessao.motivo, "Paciente não compareceu")

    def test_cancelar_sessao_registra_motivo(self):
        sessao = self.criar_sessao()
        response = self.client.post(
            reverse("atualizar_status_sessao", args=[sessao.pk]),
            {"status": "cancelada", "motivo": "Feriado municipal"},
        )
        self.assertEqual(response.status_code, 302)
        sessao.refresh_from_db()
        self.assertEqual(sessao.status, SessaoTratamento.Status.CANCELADA)
        self.assertEqual(sessao.motivo, "Feriado municipal")

    def test_falta_nao_baixa_estoque(self):
        sessao = self.criar_sessao()
        self.client.post(
            reverse("atualizar_status_sessao", args=[sessao.pk]),
            {"status": "faltou", "motivo": "Teste"},
        )
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade_atual, 10)
        self.assertFalse(
            MovimentacaoEstoque.objects.filter(tipo=MovimentacaoEstoque.TipoMovimentacao.SAIDA).exists()
        )

    def test_relatorios_calculam_taxa_de_faltas_e_consumo(self):
        realizada = self.criar_sessao(horas=2)
        faltou = self.criar_sessao(horas=3)
        SessaoTratamento.objects.filter(pk=realizada.pk).update(
            status=SessaoTratamento.Status.REALIZADA
        )
        SessaoTratamento.objects.filter(pk=faltou.pk).update(
            status=SessaoTratamento.Status.FALTOU, motivo="Abstenção"
        )
        MovimentacaoEstoque.objects.create(
            clinica=self.clinica,
            lote=self.lote,
            tipo=MovimentacaoEstoque.TipoMovimentacao.SAIDA,
            quantidade=-2,
            usuario=self.user,
        )
        response = self.client.get(reverse("relatorios"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "50,0%")
        self.assertContains(response, "Med Faltas")
        self.assertContains(response, "Frasco 10 mg")
        self.assertContains(response, "2")

    def test_relatorios_destacam_lote_com_validade_critica(self):
        lote_critico = Lote.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            numero_lote="LOT-URGENTE",
            data_validade=timezone.localdate() + timedelta(days=10),
            quantidade_inicial=5,
            quantidade_atual=5,
        )
        response = self.client.get(reverse("relatorios"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LOT-URGENTE")
        self.assertContains(response, "Validade crítica")
        self.assertEqual(lote_critico.status_validade, "critico")
