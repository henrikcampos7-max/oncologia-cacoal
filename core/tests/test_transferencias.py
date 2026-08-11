from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Apresentacao,
    Clinica,
    ItemTransferencia,
    Lote,
    Medicamento,
    MovimentacaoEstoque,
    PerfilUsuario,
    RegistroAuditoria,
    Transferencia,
)


class TransferenciaFlowTests(TestCase):
    def setUp(self):
        self.clinica_origem = Clinica.objects.create(nome="Clínica Origem")
        self.clinica_destino = Clinica.objects.create(nome="Clínica Destino")
        self.user = get_user_model().objects.create_user(
            username="transferadmin", password="Password123456789!"
        )
        self.perfil = PerfilUsuario.objects.create(
            usuario=self.user,
            clinica=self.clinica_origem,
            papel=PerfilUsuario.Papel.ADMINISTRADOR,
            ativo=True,
        )
        self.client.login(username="transferadmin", password="Password123456789!")

        self.medicamento = Medicamento.objects.create(
            clinica=self.clinica_origem, nome="OncoMed Transf", principio_ativo="Ativo"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="1 mg/mL",
            descricao="Frasco 100 mg",
            quantidade_mg=Decimal("100"),
        )
        self.lote = Lote.objects.create(
            clinica=self.clinica_origem,
            apresentacao=self.apresentacao,
            numero_lote="LOT-TRANSF",
            data_validade=timezone.localdate() + timedelta(days=180),
            quantidade_inicial=20,
            quantidade_atual=20,
        )

    def test_view_transferencias_acessivel(self):
        response = self.client.get(reverse("transferencias"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LOT-TRANSF" and "Frasco 100 mg")

    def test_cria_transferencia_com_saldo(self):
        response = self.client.post(
            reverse("transferencias"),
            {
                "criar_transferencia": "1",
                "clinica_destino": self.clinica_destino.pk,
                f"qtd_{self.apresentacao.pk}": "5",
                "observacao": "Teste de transferência",
            },
        )
        self.assertEqual(response.status_code, 302)
        transferencia = Transferencia.objects.get()
        self.assertEqual(transferencia.clinica_destino, self.clinica_destino)
        self.assertEqual(transferencia.status, Transferencia.Status.RASCUNHO)
        self.assertTrue(transferencia.numero.startswith("TR-"))
        self.assertEqual(transferencia.itens.get().quantidade, 5)

    def test_nao_cria_transferencia_acima_do_disponivel(self):
        response = self.client.post(
            reverse("transferencias"),
            {
                "criar_transferencia": "1",
                "clinica_destino": self.clinica_destino.pk,
                f"qtd_{self.apresentacao.pk}": "999",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Transferencia.objects.exists())

    def test_enviar_transferencia_baixa_estoque_na_origem(self):
        transferencia = Transferencia.objects.create(
            clinica_origem=self.clinica_origem,
            clinica_destino=self.clinica_destino,
            numero="TR-TESTE-0001",
            criado_por=self.user,
        )
        ItemTransferencia.objects.create(
            transferencia=transferencia, apresentacao=self.apresentacao, quantidade=5
        )
        response = self.client.post(
            reverse("detalhe_transferencia", kwargs={"pk": transferencia.pk}), {"acao": "enviar"}
        )
        self.assertEqual(response.status_code, 302)
        transferencia.refresh_from_db()
        self.assertEqual(transferencia.status, Transferencia.Status.EM_TRANSITO)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade_atual, 15)
        saida = MovimentacaoEstoque.objects.filter(
            lote=self.lote, tipo=MovimentacaoEstoque.TipoMovimentacao.SAIDA
        )
        self.assertTrue(saida.exists())
        self.assertTrue(RegistroAuditoria.objects.filter(clinica=self.clinica_origem).exists())

    def test_receber_transferencia_cria_lote_no_destino(self):
        usuario_destino = get_user_model().objects.create_user(
            username="destinoadmin", password="Password123456789!"
        )
        PerfilUsuario.objects.create(
            usuario=usuario_destino,
            clinica=self.clinica_destino,
            papel=PerfilUsuario.Papel.ADMINISTRADOR,
            ativo=True,
        )
        self.client.login(username="destinoadmin", password="Password123456789!")

        transferencia = Transferencia.objects.create(
            clinica_origem=self.clinica_origem,
            clinica_destino=self.clinica_destino,
            numero="TR-TESTE-0002",
            criado_por=self.user,
            status=Transferencia.Status.EM_TRANSITO,
        )
        item = ItemTransferencia.objects.create(
            transferencia=transferencia, apresentacao=self.apresentacao, quantidade=8
        )
        hoje = timezone.localdate().isoformat()
        response = self.client.post(
            reverse("detalhe_transferencia", kwargs={"pk": transferencia.pk}),
            {
                "acao": "receber",
                f"recebido_{item.pk}": "8",
                f"lote_{item.pk}": "LOT-DESTINO-1",
                f"validade_{item.pk}": hoje,
            },
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.quantidade_recebida, 8)
        lote_destino = Lote.objects.get(numero_lote="LOT-DESTINO-1")
        self.assertEqual(lote_destino.clinica, self.clinica_destino)
        self.assertEqual(lote_destino.quantidade_atual, 8)
        transferencia.refresh_from_db()
        self.assertEqual(transferencia.status, Transferencia.Status.RECEBIDA)
        self.assertIsNotNone(transferencia.data_recebimento)
