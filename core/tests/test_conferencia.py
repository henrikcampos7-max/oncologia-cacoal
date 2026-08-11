from django.contrib.auth import get_user_model
from django.test import TestCase

from core.conferencia import (
    ESTADOS_BLOQUEADOS,
    ESTADOS_TERMINAIS,
    TransicaoInvalida,
    pode_transicionar,
    sincronizar_status_operacional,
    transicionar,
    transicoes_possiveis,
)
from core.models import Clinica, RegistroAuditoria, Transferencia


class ConferenciaStateMachineTests(TestCase):
    def setUp(self):
        self.origem = Clinica.objects.create(nome="Ji-Paraná")
        self.destino = Clinica.objects.create(nome="Cacoal")
        self.user = get_user_model().objects.create_user(
            username="conferencia", password="Password123456789!"
        )
        self.transferencia = Transferencia.objects.create(
            clinica_origem=self.origem,
            clinica_destino=self.destino,
            numero="TR-2026-0001",
        )

    def test_status_inicial_rascunho(self):
        self.assertEqual(
            self.transferencia.status_conferencia,
            Transferencia.StatusConferencia.RASCUNHO,
        )

    def test_fluxo_completo_valido(self):
        caminho = [
            Transferencia.StatusConferencia.RELATORIO_IMPORTADO,
            Transferencia.StatusConferencia.EM_TRANSITO,
            Transferencia.StatusConferencia.AGUARDANDO_RECEBIMENTO,
            Transferencia.StatusConferencia.EM_CONFERENCIA,
            Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO,
            Transferencia.StatusConferencia.APROVADA,
            Transferencia.StatusConferencia.INTEGRADA_AO_ESTOQUE,
        ]
        for destino in caminho:
            transicionar(self.transferencia, destino)
        self.assertEqual(
            self.transferencia.status_conferencia,
            Transferencia.StatusConferencia.INTEGRADA_AO_ESTOQUE,
        )

    def test_transicao_invalida_levanta_erro(self):
        with self.assertRaises(TransicaoInvalida):
            transicionar(
                self.transferencia, Transferencia.StatusConferencia.APROVADA
            )
        # Estado original preservado após erro.
        self.transferencia.refresh_from_db()
        self.assertEqual(
            self.transferencia.status_conferencia,
            Transferencia.StatusConferencia.RASCUNHO,
        )

    def test_estado_terminal_nao_aceita_transicoes(self):
        transicionar(
            self.transferencia,
            Transferencia.StatusConferencia.RELATORIO_IMPORTADO,
        )
        transicionar(
            self.transferencia, Transferencia.StatusConferencia.CANCELADA
        )
        with self.assertRaises(TransicaoInvalida):
            transicionar(
                self.transferencia,
                Transferencia.StatusConferencia.RELATORIO_IMPORTADO,
            )
        self.assertIn(
            self.transferencia.status_conferencia, ESTADOS_TERMINAIS
        )

    def test_cancelamento_permitido_em_qualquer_fase_ativa(self):
        for estado in [
            Transferencia.StatusConferencia.RELATORIO_IMPORTADO,
            Transferencia.StatusConferencia.EM_TRANSITO,
            Transferencia.StatusConferencia.AGUARDANDO_RECEBIMENTO,
            Transferencia.StatusConferencia.EM_CONFERENCIA,
            Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO,
        ]:
            self.transferencia.status_conferencia = estado
            self.assertTrue(pode_transicionar(estado, Transferencia.StatusConferencia.CANCELADA))

    def test_guardas_de_fluxo(self):
        self.assertFalse(
            pode_transicionar(
                Transferencia.StatusConferencia.RASCUNHO,
                Transferencia.StatusConferencia.EM_TRANSITO,
            )
        )
        self.assertTrue(
            pode_transicionar(
                Transferencia.StatusConferencia.EM_CONFERENCIA,
                Transferencia.StatusConferencia.DIVERGENCIA,
            )
        )
        self.assertTrue(
            pode_transicionar(
                Transferencia.StatusConferencia.DIVERGENCIA,
                Transferencia.StatusConferencia.EM_CONFERENCIA,
            )
        )

    def test_transicao_registra_auditoria(self):
        transicionar(
            self.transferencia,
            Transferencia.StatusConferencia.RELATORIO_IMPORTADO,
            usuario=self.user,
            motivo="PDF recebido",
        )
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                usuario=self.user,
                acao__contains=self.transferencia.numero,
            ).exists()
        )

    def test_sincroniza_status_operacional(self):
        transicionar(
            self.transferencia,
            Transferencia.StatusConferencia.RELATORIO_IMPORTADO,
        )
        sincronizar_status_operacional(self.transferencia)
        self.transferencia.refresh_from_db()
        self.assertEqual(self.transferencia.status, Transferencia.Status.RASCUNHO)

        transicionar(
            self.transferencia, Transferencia.StatusConferencia.EM_TRANSITO
        )
        sincronizar_status_operacional(self.transferencia)
        self.transferencia.refresh_from_db()
        self.assertEqual(self.transferencia.status, Transferencia.Status.EM_TRANSITO)

        for estado in [
            Transferencia.StatusConferencia.EM_CONFERENCIA,
            Transferencia.StatusConferencia.PENDENCIA_MANUAL,
            Transferencia.StatusConferencia.DIVERGENCIA,
            Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO,
            Transferencia.StatusConferencia.APROVADA,
            Transferencia.StatusConferencia.INTEGRADA_AO_ESTOQUE,
        ]:
            self.transferencia.status_conferencia = estado
            sincronizar_status_operacional(self.transferencia)
            self.transferencia.refresh_from_db()
            self.assertEqual(self.transferencia.status, Transferencia.Status.RECEBIDA)

    def test_transicoes_possiveis_retornam_conjunto_finito(self):
        conjunto = transicoes_possiveis(Transferencia.StatusConferencia.EM_CONFERENCIA)
        self.assertIsInstance(conjunto, frozenset)
        self.assertIn(Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO, conjunto)
        self.assertIn(Transferencia.StatusConferencia.DIVERGENCIA, conjunto)

    def test_estados_bloqueados_exigem_acao_humana(self):
        for estado in ESTADOS_BLOQUEADOS:
            self.assertIn(estado, set(Transferencia.StatusConferencia.values))