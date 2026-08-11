from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Apresentacao,
    Clinica,
    ItemPedidoCompra,
    ItemProtocolo,
    Lote,
    Medicamento,
    MovimentacaoEstoque,
    Paciente,
    PedidoCompra,
    PerfilUsuario,
    Protocolo,
    RegistroAuditoria,
    SessaoTratamento,
)


class ComprasFlowTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Clínica Compras")
        self.user = get_user_model().objects.create_user(
            username="comprasadmin", password="Password123456789!"
        )
        self.perfil = PerfilUsuario.objects.create(
            usuario=self.user,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.ADMINISTRADOR,
            ativo=True,
        )
        self.client.login(username="comprasadmin", password="Password123456789!")

        self.medicamento = Medicamento.objects.create(
            clinica=self.clinica, nome="OncoMed Compra", principio_ativo="Ativo"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="1 mg/mL",
            descricao="Frasco 100 mg",
            quantidade_mg=Decimal("100"),
        )

    def test_compras_view_gera_sugestao(self):
        hoje = timezone.localdate()
        protocolo = Protocolo.objects.create(clinica=self.clinica, nome="Proto Compra")
        ItemProtocolo.objects.create(
            protocolo=protocolo,
            apresentacao=self.apresentacao,
            ciclos="1",
            dias_ciclo="1",
            tipo_dose=ItemProtocolo.TipoDose.FIXA,
            dose_valor=Decimal("300"),
        )
        paciente = Paciente.objects.create(
            clinica=self.clinica, nome="Paciente Compra", data_inicio=hoje, protocolo=protocolo
        )
        SessaoTratamento.objects.create(
            clinica=self.clinica,
            paciente=paciente,
            protocolo=protocolo,
            data_hora=timezone.now() + timedelta(days=1),
            ciclo=1,
            dia_ciclo=1,
            status=SessaoTratamento.Status.AGENDADA,
        )
        response = self.client.get(reverse("compras"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Frasco 100 mg")

    def test_cria_pedido_e_envia_para_aprovacao(self):
        response = self.client.post(
            reverse("compras"),
            {
                "criar_pedido": "1",
                f"qtd_{self.apresentacao.pk}": "10",
                "fornecedor": "Fornecedor Teste",
                "observacao": "Pedido de teste",
            },
        )
        self.assertEqual(response.status_code, 302)
        pedido = PedidoCompra.objects.get()
        self.assertEqual(pedido.status, PedidoCompra.Status.RASCUNHO)
        self.assertTrue(pedido.numero.startswith("PC-"))
        item = pedido.itens.get()
        self.assertEqual(item.quantidade, 10)

        response = self.client.post(
            reverse("detalhe_pedido", kwargs={"pk": pedido.pk}), {"acao": "enviar"}
        )
        self.assertEqual(response.status_code, 302)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoCompra.Status.PENDENTE)
        self.assertTrue(RegistroAuditoria.objects.filter(clinica=self.clinica).exists())

    def test_aprova_e_recebe_pedido_criando_lote(self):
        pedido = PedidoCompra.objects.create(
            clinica=self.clinica, numero="PC-TESTE-0001", solicitante=self.user
        )
        item = ItemPedidoCompra.objects.create(
            pedido=pedido, apresentacao=self.apresentacao, quantidade=10
        )
        pedido.status = PedidoCompra.Status.APROVADO
        pedido.save()

        hoje = timezone.localdate().isoformat()
        response = self.client.post(
            reverse("detalhe_pedido", kwargs={"pk": pedido.pk}),
            {
                "acao": "receber",
                f"recebido_{item.pk}": "10",
                f"lote_{item.pk}": "LOT-COMPRA-1",
                f"validade_{item.pk}": hoje,
            },
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.quantidade_recebida, 10)
        lote = Lote.objects.get(numero_lote="LOT-COMPRA-1")
        self.assertEqual(lote.quantidade_atual, 10)
        entrada = MovimentacaoEstoque.objects.filter(
            lote=lote, tipo=MovimentacaoEstoque.TipoMovimentacao.ENTRADA
        )
        self.assertTrue(entrada.exists())
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, PedidoCompra.Status.RECEBIDO)
        self.assertIsNotNone(pedido.data_recebimento)

    def test_aprovar_pedido_exige_perfil_gestor_ou_admin(self):
        farma = get_user_model().objects.create_user(
            username="farmacompras", password="Password123456789!"
        )
        PerfilUsuario.objects.create(
            usuario=farma,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.FARMACEUTICO,
            ativo=True,
        )
        self.client.login(username="farmacompras", password="Password123456789!")
        pedido = PedidoCompra.objects.create(
            clinica=self.clinica, numero="PC-TESTE-0002", solicitante=farma
        )
        pedido.status = PedidoCompra.Status.PENDENTE
        pedido.save()
        response = self.client.post(
            reverse("detalhe_pedido", kwargs={"pk": pedido.pk}), {"acao": "aprovar"}
        )
        pedido.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(pedido.status, PedidoCompra.Status.PENDENTE)

    def test_perfil_leitura_nao_cria_pedido(self):
        leitor = get_user_model().objects.create_user(
            username="leitorcompras", password="Password123456789!"
        )
        PerfilUsuario.objects.create(
            usuario=leitor, clinica=self.clinica, papel=PerfilUsuario.Papel.LEITURA, ativo=True
        )
        self.client.login(username="leitorcompras", password="Password123456789!")
        response = self.client.post(
            reverse("compras"),
            {"criar_pedido": "1", f"qtd_{self.apresentacao.pk}": "5"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PedidoCompra.objects.exists())
