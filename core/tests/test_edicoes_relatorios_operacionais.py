from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Apresentacao,
    Clinica,
    ItemProtocolo,
    Lote,
    MedicacaoOral,
    Medicamento,
    MovimentacaoEstoque,
    Paciente,
    PerfilUsuario,
    Protocolo,
    RegistroAuditoria,
    SessaoTratamento,
)
from core.services import calcular_sugestao_compras


class EdicoesERelatoriosOperacionaisTests(TestCase):
    def setUp(self):
        self.hoje = timezone.localdate()
        self.clinica = Clinica.objects.create(nome="Clínica Fictícia Edição")
        self.usuario = get_user_model().objects.create_user(
            username="farmaceutico.edicao", password="Password123456789!"
        )
        PerfilUsuario.objects.create(
            usuario=self.usuario,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.FARMACEUTICO,
            ativo=True,
        )
        self.protocolo = Protocolo.objects.create(
            clinica=self.clinica,
            nome="Protocolo Fictício",
            intervalo_dias=21,
            total_ciclos=6,
        )
        self.paciente = Paciente.objects.create(
            clinica=self.clinica,
            nome="PAC-FICT-EDIT-001",
            protocolo=self.protocolo,
            data_inicio=self.hoje,
            ciclos_previstos=6,
        )
        self.medicamento = Medicamento.objects.create(
            clinica=self.clinica,
            nome="Medicamento Fictício A",
            principio_ativo="Substância fictícia A",
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="10 mg/mL",
            descricao="Frasco fictício 100 mg",
            quantidade_mg=Decimal("100"),
        )
        self.outro_medicamento = Medicamento.objects.create(
            clinica=self.clinica,
            nome="Medicamento Fictício B",
        )
        self.outra_apresentacao = Apresentacao.objects.create(
            medicamento=self.outro_medicamento,
            concentracao="20 mg/mL",
            descricao="Caixa fictícia",
            quantidade_mg=Decimal("200"),
        )
        self.lote = Lote.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            numero_lote="LOT-FICT-001",
            data_validade=self.hoje + timedelta(days=120),
            quantidade_inicial=10,
            quantidade_atual=10,
        )
        self.sessao = SessaoTratamento.objects.create(
            clinica=self.clinica,
            paciente=self.paciente,
            protocolo=self.protocolo,
            data_hora=timezone.now() + timedelta(days=1),
        )
        self.oral = MedicacaoOral.objects.create(
            clinica=self.clinica,
            paciente=self.paciente,
            medicamento=self.medicamento,
            apresentacao=self.apresentacao,
            classe=MedicacaoOral.Classe.QUIMIOTERAPIA,
            dose_prescrita="100 mg",
            posologia="Texto fictício inicial",
            quantidade_por_ciclo=2,
            data_inicio=self.hoje,
            quantidade_ciclos=4,
            intervalo_dias=30,
        )
        self.client.login(
            username="farmaceutico.edicao", password="Password123456789!"
        )

    def test_cadastro_de_medicamento_persiste_estabilidade_e_observacoes(self):
        response = self.client.post(
            reverse("medicamentos"),
            {
                "nome": "Medicamento Fictício C",
                "principio_ativo": "Substância fictícia C",
                "observacoes_medicamento": "Observação geral fictícia",
                "concentracao": "5 mg/mL",
                "apresentacao": "Frasco fictício 50 mg",
                "quantidade_mg": "50",
                "estabilidade_apos_abertura": "12",
                "unidade_estabilidade": Apresentacao.UnidadeEstabilidade.HORAS,
                "condicoes_armazenamento": "Condição fictícia",
                "observacoes_estabilidade": "Conferir referência fictícia",
                "fonte_referencia": "Bula fictícia",
                "observacoes": "Outra informação fictícia",
            },
        )
        self.assertEqual(response.status_code, 302)
        apresentacao = Apresentacao.objects.get(
            medicamento__nome="Medicamento Fictício C"
        )
        self.assertEqual(apresentacao.estabilidade_apos_abertura, Decimal("12"))
        self.assertEqual(apresentacao.unidade_estabilidade, "horas")
        self.assertEqual(apresentacao.observacoes, "Outra informação fictícia")
        self.assertEqual(
            apresentacao.medicamento.observacoes, "Observação geral fictícia"
        )

    def test_edita_agendamento_e_registra_campos_alterados(self):
        nova_data = timezone.now() + timedelta(days=2)
        response = self.client.post(
            reverse("editar_sessao", args=[self.sessao.pk]),
            {
                "paciente": self.paciente.pk,
                "protocolo": self.protocolo.pk,
                "data_hora": nova_data.strftime("%Y-%m-%dT%H:%M"),
                "ciclo": 2,
                "dia_ciclo": 1,
                "observacoes": "Alteração fictícia de agenda",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.sessao.refresh_from_db()
        self.assertEqual(self.sessao.ciclo, 2)
        registro = RegistroAuditoria.objects.filter(
            acao="Edição de agendamento"
        ).latest("pk")
        self.assertIn("campos alterados", registro.detalhes)
        self.assertIn("antes/depois", registro.detalhes)

    def test_edicao_de_sessao_confirmada_exige_nova_confirmacao(self):
        self.sessao.status = SessaoTratamento.Status.CONFIRMADA
        self.sessao.save(update_fields=["status", "atualizado_em"])
        response = self.client.post(
            reverse("editar_sessao", args=[self.sessao.pk]),
            {
                "paciente": self.paciente.pk,
                "protocolo": self.protocolo.pk,
                "data_hora": self.sessao.data_hora.strftime("%Y-%m-%dT%H:%M"),
                "ciclo": 2,
                "dia_ciclo": 1,
                "observacoes": "Requer nova conferência fictícia",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.sessao.refresh_from_db()
        self.assertEqual(self.sessao.status, SessaoTratamento.Status.AGENDADA)

    def test_edicao_de_sessao_duplicada_retorna_erro_de_formulario(self):
        horario = timezone.localtime(timezone.now() + timedelta(days=3)).replace(
            second=0, microsecond=0
        )
        SessaoTratamento.objects.create(
            clinica=self.clinica,
            paciente=self.paciente,
            protocolo=self.protocolo,
            data_hora=horario,
            ciclo=2,
            dia_ciclo=1,
        )
        response = self.client.post(
            reverse("editar_sessao", args=[self.sessao.pk]),
            {
                "paciente": self.paciente.pk,
                "protocolo": self.protocolo.pk,
                "data_hora": horario.strftime("%Y-%m-%dT%H:%M"),
                "ciclo": 2,
                "dia_ciclo": 1,
                "observacoes": "Duplicidade fictícia",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Já existe uma aplicação igual")

    def test_sessao_encerrada_nao_pode_ser_sobrescrita(self):
        self.sessao.status = SessaoTratamento.Status.REALIZADA
        self.sessao.save(update_fields=["status", "atualizado_em"])
        response = self.client.get(reverse("editar_sessao", args=[self.sessao.pk]))
        self.assertEqual(response.status_code, 409)

    def test_edicao_oral_cria_nova_versao_e_preserva_anterior(self):
        response = self.client.post(
            reverse("editar_medicacao_oral", args=[self.oral.pk]),
            {
                "paciente": self.paciente.pk,
                "classe": MedicacaoOral.Classe.QUIMIOTERAPIA,
                "medicamento": self.outro_medicamento.pk,
                "apresentacao": self.outra_apresentacao.pk,
                "dose_prescrita": "200 mg",
                "posologia": "Nova posologia fictícia",
                "quantidade_por_ciclo": 3,
                "data_inicio": self.hoje.isoformat(),
                "quantidade_ciclos": 5,
                "intervalo_dias": 28,
                "renovacao_pedido_meses": 6,
                "solicitar_guia_antes_dias": 10,
                "estrategia_aquisicao": MedicacaoOral.EstrategiaAquisicao.LISTA_PROGRAMADA,
                "motivo_prioridade": "",
                "observacoes": "Mudança médica fictícia",
                "ciclo_atual": 1,
                "motivo_alteracao": "Prescrição fictícia atualizada",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.oral.refresh_from_db()
        self.assertFalse(self.oral.vigente)
        nova = MedicacaoOral.objects.get(substitui=self.oral)
        self.assertTrue(nova.vigente)
        self.assertEqual(nova.medicamento, self.outro_medicamento)
        self.assertEqual(nova.posologia, "Nova posologia fictícia")
        self.assertEqual(nova.quantidade_ciclos, 5)
        self.assertEqual(nova.status, MedicacaoOral.Status.PREVISTA)
        self.assertIsNone(nova.revisado_por)

    def test_modelo_oral_rejeita_apresentacao_de_outro_medicamento(self):
        inconsistente = MedicacaoOral(
            clinica=self.clinica,
            paciente=self.paciente,
            medicamento=self.medicamento,
            apresentacao=self.outra_apresentacao,
            classe=MedicacaoOral.Classe.QUIMIOTERAPIA,
            data_inicio=self.hoje + timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            inconsistente.full_clean()

    def test_edita_lote_sem_alterar_saldo(self):
        response = self.client.post(
            reverse("editar_lote", args=[self.lote.pk]),
            {
                "apresentacao": self.apresentacao.pk,
                "numero_lote": "LOT-FICT-001-REV",
                "data_validade": (self.hoje + timedelta(days=180)).isoformat(),
                "estoque_minimo": 7,
                "observacoes": "Lote fictício revisado",
                "ativo": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade_atual, 10)
        self.assertEqual(self.lote.estoque_minimo, 7)
        self.assertEqual(self.lote.observacoes, "Lote fictício revisado")

    def test_lote_com_historico_nao_pode_trocar_apresentacao(self):
        MovimentacaoEstoque.objects.create(
            clinica=self.clinica,
            lote=self.lote,
            tipo=MovimentacaoEstoque.TipoMovimentacao.ENTRADA,
            quantidade=10,
            usuario=self.usuario,
        )
        response = self.client.post(
            reverse("editar_lote", args=[self.lote.pk]),
            {
                "apresentacao": self.outra_apresentacao.pk,
                "numero_lote": self.lote.numero_lote,
                "data_validade": self.lote.data_validade.isoformat(),
                "estoque_minimo": self.lote.estoque_minimo,
                "observacoes": "",
                "ativo": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.apresentacao, self.apresentacao)
        self.assertContains(response, "não pode ser trocada")

    def test_lote_com_saldo_nao_pode_ser_desativado(self):
        response = self.client.post(
            reverse("editar_lote", args=[self.lote.pk]),
            {
                "apresentacao": self.apresentacao.pk,
                "numero_lote": self.lote.numero_lote,
                "data_validade": self.lote.data_validade.isoformat(),
                "estoque_minimo": self.lote.estoque_minimo,
                "observacoes": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.lote.refresh_from_db()
        self.assertTrue(self.lote.ativo)
        self.assertContains(response, "Zere o saldo e as reservas")

    def test_saida_acima_do_disponivel_e_rejeitada(self):
        response = self.client.post(
            reverse("estoque"),
            {
                "salvar_movimentacao": "1",
                "mov-lote": self.lote.pk,
                "mov-tipo": MovimentacaoEstoque.TipoMovimentacao.SAIDA,
                "mov-quantidade": 11,
                "mov-observacao": "Tentativa fictícia inválida",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade_atual, 10)
        self.assertFalse(self.lote.movimentacoes.exists())
        self.assertContains(response, "não pode superar o saldo disponível")

    def test_ajuste_nao_pode_deixar_saldo_abaixo_da_reserva(self):
        MovimentacaoEstoque.objects.create(
            clinica=self.clinica,
            lote=self.lote,
            tipo=MovimentacaoEstoque.TipoMovimentacao.RESERVA,
            quantidade=8,
            usuario=self.usuario,
        )
        response = self.client.post(
            reverse("estoque"),
            {
                "salvar_movimentacao": "1",
                "mov-lote": self.lote.pk,
                "mov-tipo": MovimentacaoEstoque.TipoMovimentacao.AJUSTE,
                "mov-quantidade": -3,
                "mov-observacao": "Ajuste fictício inválido",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade_atual, 10)
        self.assertEqual(self.lote.movimentacoes.count(), 1)
        self.assertContains(response, "abaixo da quantidade reservada")

    def test_relatorio_de_medicamento_especifico_combina_iv_e_oral(self):
        ItemProtocolo.objects.create(
            protocolo=self.protocolo,
            apresentacao=self.apresentacao,
            ciclos="1",
            dias_ciclo="1",
            tipo_dose=ItemProtocolo.TipoDose.FIXA,
            dose_valor=Decimal("100"),
        )
        response = self.client.get(
            reverse("relatorio_operacional_csv"),
            {
                "tipo": "medicamento_periodo",
                "data_inicial": self.hoje.isoformat(),
                "data_final": (self.hoje + timedelta(days=40)).isoformat(),
                "medicamento": self.medicamento.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        conteudo = response.content.decode("utf-8-sig")
        self.assertIn("Oral", conteudo)
        self.assertIn("Infusional", conteudo)
        self.assertIn("Medicamento Fictício A", conteudo)

    def test_relatorio_neutraliza_formula_em_nome(self):
        Paciente.objects.create(
            clinica=self.clinica,
            nome="=PAC-FICT-FORMULA",
            data_inicio=self.hoje,
        )
        response = self.client.get(
            reverse("relatorio_operacional_csv"),
            {
                "tipo": "pacientes",
                "data_inicial": self.hoje.isoformat(),
                "data_final": self.hoje.isoformat(),
            },
        )
        self.assertContains(response, "'=PAC-FICT-FORMULA")

    def test_relatorio_de_pacientes_respeita_periodo_de_inicio(self):
        Paciente.objects.create(
            clinica=self.clinica,
            nome="PAC-FICT-FORA-PERIODO",
            data_inicio=self.hoje - timedelta(days=20),
        )
        response = self.client.get(
            reverse("relatorio_operacional_csv"),
            {
                "tipo": "pacientes",
                "data_inicial": self.hoje.isoformat(),
                "data_final": self.hoje.isoformat(),
            },
        )
        conteudo = response.content.decode("utf-8-sig")
        self.assertIn(self.paciente.nome, conteudo)
        self.assertNotIn("PAC-FICT-FORA-PERIODO", conteudo)

    def test_quantitativo_inclui_previsao_oral(self):
        response = self.client.get(
            reverse("quantitativo"),
            {
                "data_inicial": self.hoje.isoformat(),
                "data_final": (self.hoje + timedelta(days=35)).isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_unidades_orais"], 4)
        self.assertContains(response, "Medicamento Fictício A")

    def test_previsao_oral_ignora_ciclos_anteriores_ao_atual(self):
        self.oral.ciclo_atual = 3
        self.oral.save(update_fields=["ciclo_atual", "atualizado_em"])
        response = self.client.get(
            reverse("quantitativo"),
            {
                "data_inicial": self.hoje.isoformat(),
                "data_final": (self.hoje + timedelta(days=120)).isoformat(),
            },
        )
        self.assertEqual(response.context["total_unidades_orais"], 4)

    def test_previsao_de_compra_ignora_versao_oral_substituida(self):
        self.oral.vigente = False
        self.oral.save(update_fields=["vigente", "atualizado_em"])
        MedicacaoOral.objects.create(
            clinica=self.clinica,
            paciente=self.paciente,
            medicamento=self.medicamento,
            apresentacao=self.apresentacao,
            classe=MedicacaoOral.Classe.QUIMIOTERAPIA,
            quantidade_por_ciclo=2,
            data_inicio=self.hoje,
            quantidade_ciclos=4,
            intervalo_dias=30,
            substitui=self.oral,
        )

        sugestao = next(
            item
            for item in calcular_sugestao_compras(
                self.clinica, dias=30, margem_seguranca=0
            )
            if item["apresentacao"] == self.apresentacao
        )

        self.assertEqual(sugestao["unidades_orais"], 4)
