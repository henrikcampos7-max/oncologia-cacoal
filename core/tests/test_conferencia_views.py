from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import (
    TransferenciaEvidencia,
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
from core.tests.test_relatorio_pdf import montar_pdf

PASSWORD = "Password123456789!"


def _pdf(nome="relatorio.pdf", *linhas):
    return SimpleUploadedFile(
        nome,
        montar_pdf(
            *(
                linhas
                or [
                    "UNIMEDJPR 02/07/2026 10:46",
                    "Destino: Cacoal - Estoque: Estoque Principal Cacoal",
                    "Tipo de Insumo: Medicamento",
                    "3,0000 5,0000DOXORRUBICINA 2 MG/ML DOXORRUBICINA 2 MG/ML SOL INJ LOTEDOX1",
                ]
            )
        ),
        content_type="application/pdf",
    )


class ConferenciaViewsTests(TestCase):
    def setUp(self):
        self.jiparana = Clinica.objects.create(nome="Ji-Paraná")
        self.cacoal = Clinica.objects.create(nome="Cacoal")
        self.user = get_user_model().objects.create_user(username="conf", password=PASSWORD)
        self.perfil = self.cacoal.perfis.create(
            usuario=self.user,
            papel=self.perfil_papel(),
            ativo=True,
        )
        self.client.login(username="conf", password=PASSWORD)
        self.medicamento = Medicamento.objects.create(
            clinica=self.cacoal, nome="Doxorrubicina", principio_ativo="Doxorrubicina"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="2 mg/mL",
            descricao="Frasco 50 mg",
            quantidade_mg=50,
        )

    def perfil_papel(self):
        from core.models import PerfilUsuario

        return PerfilUsuario.Papel.FARMACEUTICO

    def _importar(self):
        return self.client.post(
            reverse("importar_relatorio_conferencia"),
            {"clinica_origem": self.jiparana.pk, "relatorio": _pdf()},
        )

    def _transferencia(self):
        self._importar()
        return Transferencia.objects.get()

    def test_importar_relatorio_pdf(self):
        response = self._importar()
        self.assertEqual(response.status_code, 302)
        transferencia = Transferencia.objects.get()
        self.assertEqual(transferencia.clinica_origem, self.jiparana)
        self.assertEqual(transferencia.clinica_destino, self.cacoal)
        self.assertEqual(ItemTransferencia.objects.filter(transferencia=transferencia).count(), 1)
        self.assertTrue(transferencia.relatorio_arquivo)

    def test_importar_rejeita_nao_pdf(self):
        self.assertIn(
            self.client.post(
                reverse("importar_relatorio_conferencia"),
                {
                    "clinica_origem": self.jiparana.pk,
                    "relatorio": SimpleUploadedFile("x.txt", b"abc", content_type="text/plain"),
                },
            ).status_code,
            (302,),
        )
        self.assertEqual(Transferencia.objects.count(), 0)

    def test_conferencia_requer_login_e_permissao(self):
        self.client.logout()
        resposta = self.client.get(reverse("conferencia_transferencia", kwargs={"pk": 1}))
        self.assertEqual(resposta.status_code, 302)

    def test_fluxo_completo_aprovacao_e_integracao(self):
        transferencia = self._transferencia()
        item = ItemTransferencia.objects.get(transferencia=transferencia)

        response = self.client.post(
            reverse("conferencia_transferencia", kwargs={"pk": transferencia.pk}),
            {
                "acao": "adicionar_evidencia",
                "item": item.pk,
                "foto": SimpleUploadedFile(
                    "foto.png", b"\x89PNG", content_type="image/png"
                ),
                "lote": "LOTEDOX1",
                "validade": "2026-12-15",
                "quantidade": "3",
            },
        )
        self.assertEqual(response.status_code, 302)
        transferencia.refresh_from_db()
        self.assertEqual(
            transferencia.status_conferencia,
            Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO,
        )

        response = self.client.post(
            reverse("conferencia_transferencia", kwargs={"pk": transferencia.pk}),
            {"acao": "aprovar"},
        )
        transferencia.refresh_from_db()
        self.assertEqual(
            transferencia.status_conferencia, Transferencia.StatusConferencia.APROVADA
        )

        response = self.client.post(
            reverse("conferencia_transferencia", kwargs={"pk": transferencia.pk}),
            {"acao": "integrar_estoque"},
        )
        transferencia.refresh_from_db()
        self.assertEqual(
            transferencia.status_conferencia,
            Transferencia.StatusConferencia.INTEGRADA_AO_ESTOQUE,
        )
        lote = Lote.objects.get(apresentacao=self.apresentacao, numero_lote="LOTEDOX1")
        self.assertEqual(lote.quantidade_atual, 3)
        self.assertTrue(
            MovimentacaoEstoque.objects.filter(
                lote=lote, tipo=MovimentacaoEstoque.TipoMovimentacao.ENTRADA
            ).exists()
        )

    def test_integrar_sem_aprovacao_e_rejeitado(self):
        transferencia = self._transferencia()
        transferencia.status_conferencia = Transferencia.StatusConferencia.EM_CONFERENCIA
        transferencia.save(update_fields=["status_conferencia"])
        response = self.client.post(
            reverse("conferencia_transferencia", kwargs={"pk": transferencia.pk}),
            {"acao": "integrar_estoque"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Lote.objects.exists())

    def test_evidencia_sem_lote_exige_revisao(self):
        transferencia = self._transferencia()
        item = ItemTransferencia.objects.get(transferencia=transferencia)
        self.client.post(
            reverse("conferencia_transferencia", kwargs={"pk": transferencia.pk}),
            {
                "acao": "adicionar_evidencia",
                "item": item.pk,
                "foto": SimpleUploadedFile("f2.png", b"\x89PNG", content_type="image/png"),
            },
        )
        transferencia.refresh_from_db()
        self.assertEqual(
            transferencia.status_conferencia,
            Transferencia.StatusConferencia.DIVERGENCIA,
        )

    def test_resolver_divergencia_pela_tela(self):
        transferencia = self._transferencia()
        item = ItemTransferencia.objects.get(transferencia=transferencia)
        divergencia = DivergenciaTransferencia.objects.create(
            transferencia=transferencia,
            item=item,
            tipo=DivergenciaTransferencia.Tipo.QUANTIDADE,
            valor_esperado="3",
            valor_observado="99",
        )
        response = self.client.post(
            reverse("conferencia_transferencia", kwargs={"pk": transferencia.pk}),
            {"acao": "resolver_divergencia", "divergencia": divergencia.pk, "resolucao": "corrigido"},
        )
        self.assertEqual(response.status_code, 302)
        divergencia.refresh_from_db()
        self.assertEqual(
            divergencia.status, DivergenciaTransferencia.StatusResolucao.RESOLVIDA
        )

    def test_tela_conferencia_lista_dados(self):
        transferencia = self._transferencia()
        response = self.client.get(
            reverse("conferencia_transferencia", kwargs={"pk": transferencia.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Conferência")
        self.assertContains(response, "Doxorrubicina")

    def test_importar_duplicado_rejeitado_pela_view(self):
        self._importar()
        response = self.client.post(
            reverse("importar_relatorio_conferencia"),
            {"clinica_origem": self.jiparana.pk, "relatorio": _pdf()},
        )
        self.assertEqual(Transferencia.objects.count(), 1)

    def test_confirmacao_manual_sem_foto_reconcilia_o_item(self):
        transferencia = self._transferencia()
        item = ItemTransferencia.objects.get(transferencia=transferencia)
        response = self.client.post(
            reverse("conferencia_transferencia", kwargs={"pk": transferencia.pk}),
            {
                "acao": "confirmar_item",
                "item": item.pk,
                "lote": "LOTEDOX1",
                "validade": "2026-12-15",
                "quantidade": "3",
            },
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status_reconciliacao, StatusReconciliacao.CONFORME)
        self.assertFalse(TransferenciaEvidencia.objects.exists())
        transferencia.refresh_from_db()
        self.assertEqual(
            transferencia.status_conferencia,
            Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO,
        )

    def test_confirmacao_manual_exige_lote_e_validade(self):
        transferencia = self._transferencia()
        item = ItemTransferencia.objects.get(transferencia=transferencia)
        response = self.client.post(
            reverse("conferencia_transferencia", kwargs={"pk": transferencia.pk}),
            {"acao": "confirmar_item", "item": item.pk, "lote": ""},
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status_reconciliacao, StatusReconciliacao.NAO_FOTOGRAFADO)
        transferencia.refresh_from_db()
        self.assertEqual(
            transferencia.status_conferencia,
            Transferencia.StatusConferencia.RELATORIO_IMPORTADO,
        )

    def test_confirmacao_manual_lote_divergente_gera_divergencia(self):
        transferencia = self._transferencia()
        item = ItemTransferencia.objects.get(transferencia=transferencia)
        response = self.client.post(
            reverse("conferencia_transferencia", kwargs={"pk": transferencia.pk}),
            {
                "acao": "confirmar_item",
                "item": item.pk,
                "lote": "OUTROLOTE",
                "validade": "2026-12-15",
                "quantidade": "3",
            },
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(
            item.status_reconciliacao, StatusReconciliacao.DIVERGENCIA_LOTE
        )
        self.assertTrue(
            DivergenciaTransferencia.objects.filter(
                item=item, tipo=DivergenciaTransferencia.Tipo.LOTE
            ).exists()
        )
        self.assertEqual(response.status_code, 302)