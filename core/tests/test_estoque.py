from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.models import Apresentacao, Clinica, Lote, Medicamento, MovimentacaoEstoque


class EstoqueModelTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Clínica Teste")
        self.medicamento = Medicamento.objects.create(
            clinica=self.clinica, nome="OncoMed Teste", principio_ativo="Ativo Teste"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="10 mg/mL",
            descricao="Frasco 100 mg",
            quantidade_mg=Decimal("100"),
        )

    def test_lote_status_validade_e_estoque(self):
        hoje = timezone.localdate()
        lote = Lote.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            numero_lote="LOT-001",
            data_validade=hoje + timedelta(days=20),
            quantidade_inicial=50,
            quantidade_atual=3,
            estoque_minimo=5,
        )

        self.assertEqual(lote.status_validade, "critico")
        self.assertEqual(lote.status_estoque, "baixo")
        self.assertTrue("LOT-001" in str(lote))

    def test_movimentacao_estoque(self):
        hoje = timezone.localdate()
        lote = Lote.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            numero_lote="LOT-002",
            data_validade=hoje + timedelta(days=100),
            quantidade_inicial=10,
            quantidade_atual=10,
        )
        mov = MovimentacaoEstoque.objects.create(
            clinica=self.clinica,
            lote=lote,
            tipo=MovimentacaoEstoque.TipoMovimentacao.SAIDA,
            quantidade=-2,
            observacao="Teste de saída",
        )
        self.assertEqual(mov.tipo, "saida")
        self.assertEqual(mov.quantidade, -2)
        self.assertTrue("LOT-002" in str(mov))
