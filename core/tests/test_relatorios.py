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

    def test_relatorios_filtram_por_mes(self):
        primeiro_mes_passado = (timezone.localdate().replace(day=1) - timedelta(days=1)).replace(day=1)
        response = self.client.get(
            reverse("relatorios"), {"mes": primeiro_mes_passado.strftime("%Y-%m")}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_sessoes_mes"], 0)
        self.assertEqual(response.context["taxa_faltas"], 0)
        self.assertNotEqual(
            response.context["inicio_mes"].strftime("%Y-%m"),
            timezone.localdate().strftime("%Y-%m"),
        )

    def test_relatorios_mostram_reaproveitamento_e_operacao_do_mes(self):
        from core.models import PedidoCompra, SobraReal, Transferencia

        paciente_destino = Paciente.objects.create(
            clinica=self.clinica,
            nome="Paciente Destino",
            data_inicio=timezone.localdate(),
        )
        sobra = SobraReal.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            quantidade_mg=Decimal("40"),
            lote=self.lote,
            data_abertura=timezone.now(),
            limite_estabilidade=timezone.now() + timedelta(hours=12),
        )
        sobra.reutilizar(paciente_destino, self.user)
        sobra2 = SobraReal.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            quantidade_mg=Decimal("15"),
            lote=self.lote,
            data_abertura=timezone.now() - timedelta(hours=1),
            limite_estabilidade=timezone.now() - timedelta(minutes=30),
        )
        sobra2.descartar("Contaminação suspeita", self.user)
        PedidoCompra.objects.create(
            clinica=self.clinica,
            numero="PC-TESTE-0001",
            status=PedidoCompra.Status.RECEBIDO,
            solicitante=self.user,
        )
        Transferencia.objects.create(
            clinica_origem=Clinica.objects.create(nome="Origem Relatórios"),
            clinica_destino=self.clinica,
            numero="TR-JP-2026-777",
            importada=True,
            status=Transferencia.Status.RECEBIDA,
            data_recebimento=timezone.now(),
        )

        response = self.client.get(reverse("relatorios"))
        self.assertEqual(response.status_code, 200)
        contexto = response.context
        self.assertEqual(contexto["sobras_reutilizadas_qtd"], 1)
        self.assertEqual(contexto["sobras_reutilizadas_mg"], 40.0)
        self.assertEqual(contexto["sobras_descartadas_qtd"], 1)
        self.assertEqual(contexto["sobras_descartadas_mg"], 15.0)
        self.assertEqual(contexto["pedidos_criados_mes"], 1)
        self.assertEqual(contexto["pedidos_recebidos_mes"], 1)
        self.assertEqual(contexto["transferencias_recebidas_mes"], 1)
        self.assertContains(response, "Reutilizada")
        self.assertContains(response, "Contaminação suspeita")

    def test_consumo_csv_exporta_saidas_do_mes(self):
        MovimentacaoEstoque.objects.create(
            clinica=self.clinica,
            lote=self.lote,
            tipo=MovimentacaoEstoque.TipoMovimentacao.SAIDA,
            quantidade=-2,
            usuario=self.user,
        )
        response = self.client.get(reverse("relatorios_consumo_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        conteudo = response.content.decode("utf-8-sig")
        self.assertIn("Med Faltas", conteudo)
        self.assertIn("Frasco 10 mg", conteudo)
        self.assertIn(";2", conteudo)
