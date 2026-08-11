from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.models import (
    Apresentacao,
    Clinica,
    DivergenciaTransferencia,
    ItemTransferencia,
    Lote,
    Medicamento,
    MovimentacaoEstoque,
    ReconciliacaoItemTransferencia,
    StatusReconciliacao,
    Transferencia,
)
from core.reconciliacao import (
    classificar_validade,
    criar_reconciliacoes_para_transferencia,
    derivar_status_conferencia,
    integrar_ao_estoque,
    reconciliar_item,
    registrar_divergencia,
    resolver_divergencia,
)


class BaseReconciliacaoTests(TestCase):
    def setUp(self):
        self.origem = Clinica.objects.create(nome="Ji-Paraná")
        self.destino = Clinica.objects.create(nome="Cacoal")
        self.user = get_user_model().objects.create_user(
            username="recon", password="Password123456789!"
        )
        self.medicamento = Medicamento.objects.create(
            clinica=self.destino, nome="Bevacizumabe", principio_ativo="Bevacizumabe"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="25 mg/mL",
            descricao="Frasco 400 mg",
            quantidade_mg=400,
        )
        self.transferencia = Transferencia.objects.create(
            clinica_origem=self.origem,
            clinica_destino=self.destino,
            numero="TR-REC-001",
            status_conferencia=Transferencia.StatusConferencia.EM_CONFERENCIA,
        )
        self.item = ItemTransferencia.objects.create(
            transferencia=self.transferencia,
            apresentacao=self.apresentacao,
            quantidade=4,
        )

    def _observado_conforme(self, **extra):
        dados = {
            "produto_observado": self.apresentacao,
            "lote": "BEV-2026-01",
            "validade": date(2028, 6, 1),
            "quantidade": 4,
            "foto_insuficiente": False,
            "confianca_final": 0.99,
        }
        dados.update(extra)
        return dados


class ClassificarValidadeTests(TestCase):
    def test_ok_critica_vencida_desconhecida(self):
        hoje = date(2026, 1, 1)
        self.assertEqual(classificar_validade(date(2026, 3, 1), hoje=hoje), "ok")
        self.assertEqual(classificar_validade(date(2026, 1, 20), hoje=hoje), "critica")
        self.assertEqual(classificar_validade(date(2025, 12, 31), hoje=hoje), "vencida")
        self.assertEqual(classificar_validade(None, hoje=hoje), "desconhecida")


class ReconciliarItemTests(BaseReconciliacaoTests):
    def test_item_conforme(self):
        replay = reconciliar_item(self.item, self._observado_conforme(), usuario=self.user)
        self.assertEqual(replay.status_final, StatusReconciliacao.CONFORME)
        self.assertIs(replay.match_produto, True)
        self.assertIs(replay.match_lote, True)
        self.assertIs(replay.match_quantidade, True)
        self.assertFalse(
            DivergenciaTransferencia.objects.filter(item=self.item).exists()
        )

    def test_produto_diferente_cria_divergencia_critica(self):
        outro_medicamento = Medicamento.objects.create(
            clinica=self.destino, nome="Pembrolizumabe", principio_ativo="Pembrolizumabe"
        )
        outro = Apresentacao.objects.create(
            medicamento=outro_medicamento,
            concentracao="25 mg/mL",
            descricao="Frasco 100 mg",
            quantidade_mg=100,
        )
        replay = reconciliar_item(
            self.item, self._observado_conforme(produto_observado=outro), usuario=self.user
        )
        self.assertEqual(replay.status_final, StatusReconciliacao.DIVERGENCIA_PRODUTO)
        divergencia = DivergenciaTransferencia.objects.get(item=self.item)
        self.assertEqual(divergencia.tipo, DivergenciaTransferencia.Tipo.PRODUTO)
        self.assertEqual(divergencia.severidade, DivergenciaTransferencia.Severidade.CRITICA)

    def test_produto_nao_identificado(self):
        replay = reconciliar_item(
            self.item, self._observado_conforme(produto_observado=None), usuario=self.user
        )
        self.assertEqual(replay.status_final, StatusReconciliacao.DIVERGENCIA_APRESENTACAO)

    def test_quantidade_divergente(self):
        replay = reconciliar_item(
            self.item, self._observado_conforme(quantidade=2), usuario=self.user
        )
        self.assertEqual(replay.status_final, StatusReconciliacao.DIVERGENCIA_QUANTIDADE)
        self.assertIs(replay.match_quantidade, False)

    def test_validade_vencida_critica(self):
        replay = reconciliar_item(
            self.item,
            self._observado_conforme(validade=timezone.localdate() - timedelta(days=5)),
        )
        self.assertEqual(replay.status_final, StatusReconciliacao.DIVERGENCIA_VALIDADE)

        replay = reconciliar_item(
            self.item,
            self._observado_conforme(validade=timezone.localdate() + timedelta(days=10)),
        )
        self.assertEqual(replay.status_final, StatusReconciliacao.VALIDADE_CRITICA)

    def test_validade_desconhecida_nao_e_divergente(self):
        replay = reconciliar_item(
            self.item, self._observado_conforme(validade=None, lote=""), usuario=self.user
        )
        self.assertEqual(replay.status_final, StatusReconciliacao.CONFORME)
        self.assertIsNone(replay.match_lote)

    def test_foto_insuficiente(self):
        replay = reconciliar_item(
            self.item, self._observado_conforme(foto_insuficiente=True), usuario=self.user
        )
        self.assertEqual(replay.status_final, StatusReconciliacao.FOTO_INSUFICIENTE)
        divergencia = DivergenciaTransferencia.objects.get(item=self.item)
        self.assertEqual(
            divergencia.tipo, DivergenciaTransferencia.Tipo.FOTO_INSUFICIENTE
        )


class DerivarStatusConferenciaTests(BaseReconciliacaoTests):
    def test_tudo_conforme_pronta_para_aprovacao(self):
        reconciliar_item(self.item, self._observado_conforme(), usuario=self.user)
        derivar_status_conferencia(self.transferencia, usuario=self.user)
        self.transferencia.refresh_from_db()
        self.assertEqual(
            self.transferencia.status_conferencia,
            Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO,
        )

    def test_divergencia_leva_a_estado_divergencia(self):
        reconciliar_item(
            self.item, self._observado_conforme(quantidade=99), usuario=self.user
        )
        derivar_status_conferencia(self.transferencia, usuario=self.user)
        self.transferencia.refresh_from_db()
        self.assertEqual(
            self.transferencia.status_conferencia,
            Transferencia.StatusConferencia.DIVERGENCIA,
        )
        self.item.refresh_from_db()
        self.assertEqual(
            self.item.status_reconciliacao, StatusReconciliacao.DIVERGENCIA_QUANTIDADE
        )

    def test_pendente_nao_fotografado_mantem_em_conferencia(self):
        derivar_status_conferencia(self.transferencia, usuario=self.user)
        self.transferencia.refresh_from_db()
        self.assertEqual(
            self.transferencia.status_conferencia,
            Transferencia.StatusConferencia.EM_CONFERENCIA,
        )

    def test_resolver_divergencia_permite_avanco(self):
        reconciliar_item(
            self.item, self._observado_conforme(quantidade=99), usuario=self.user
        )
        derivar_status_conferencia(self.transferencia, usuario=self.user)
        divergencia = DivergenciaTransferencia.objects.get(item=self.item)
        resolver_divergencia(divergencia, self.user, "Foi erro de digitação: 4.")
        reconciliar_item(self.item, self._observado_conforme(), usuario=self.user)
        derivar_status_conferencia(self.transferencia, usuario=self.user)
        self.transferencia.refresh_from_db()
        self.assertEqual(
            self.transferencia.status_conferencia,
            Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO,
        )


class IntegrarAoEstoqueTests(BaseReconciliacaoTests):
    def _aprovar(self):
        self.transferencia.status_conferencia = Transferencia.StatusConferencia.APROVADA
        self.transferencia.save(update_fields=["status_conferencia"])

    def test_integracao_exige_aprovacao(self):
        with self.assertRaises(ValueError):
            integrar_ao_estoque(self.transferencia, self.user)

    def test_integra_lote_e_movimentacao(self):
        reconciliar_item(self.item, self._observado_conforme(), usuario=self.user)
        self._aprovar()
        entradas = integrar_ao_estoque(self.transferencia, self.user)
        self.assertEqual(len(entradas), 1)
        lote = Lote.objects.get(
            clinica=self.destino, apresentacao=self.apresentacao, numero_lote="BEV-2026-01"
        )
        self.assertEqual(lote.quantidade_atual, 4)
        mov = MovimentacaoEstoque.objects.get(
            lote=lote, tipo=MovimentacaoEstoque.TipoMovimentacao.ENTRADA
        )
        self.assertEqual(mov.quantidade, 4)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantidade_recebida, 4)
        self.transferencia.refresh_from_db()
        self.assertIsNotNone(self.transferencia.data_recebimento)

    def test_lote_existente_acumula_estoque(self):
        reconciliar_item(self.item, self._observado_conforme(), usuario=self.user)
        Lote.objects.create(
            clinica=self.destino,
            apresentacao=self.apresentacao,
            numero_lote="BEV-2026-01",
            data_validade=date(2028, 6, 1),
            quantidade_inicial=10,
            quantidade_atual=10,
        )
        self._aprovar()
        integrar_ao_estoque(self.transferencia, self.user)
        lote = Lote.objects.get(numero_lote="BEV-2026-01")
        self.assertEqual(lote.quantidade_atual, 14)

    def test_sem_lote_observado_usar_placeholder(self):
        reconciliar_item(
            self.item, self._observado_conforme(lote="", validade=None), usuario=self.user
        )
        self._aprovar()
        integrar_ao_estoque(self.transferencia, self.user)
        self.assertTrue(
            Lote.objects.filter(
                clinica=self.destino, numero_lote="SEM-LOTE-TRANSF"
            ).exists()
        )


class ReconciliacoesExtrasTests(BaseReconciliacaoTests):
    def test_criar_reconciliacoes_e_idempotente(self):
        self.assertEqual(criar_reconciliacoes_para_transferencia(self.transferencia), 1)
        self.assertEqual(criar_reconciliacoes_para_transferencia(self.transferencia), 0)
        self.assertEqual(ReconciliacaoItemTransferencia.objects.count(), 1)

    def test_registrar_divergencia_tipada(self):
        registrar_divergencia(
            self.transferencia,
            DivergenciaTransferencia.Tipo.ITEM_AUSENTE,
            "X",
            "Faltou",
            severidade=DivergenciaTransferencia.Severidade.CRITICA,
            item=self.item,
        )
        div = DivergenciaTransferencia.objects.get(item=self.item)
        self.assertEqual(div.tipo, DivergenciaTransferencia.Tipo.ITEM_AUSENTE)
        self.assertEqual(div.status, DivergenciaTransferencia.StatusResolucao.PENDENTE)