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

    def test_baixa_estoque_por_sessao(self):
        from core.models import ItemProtocolo, Paciente, Protocolo, SessaoTratamento
        from core.services import processar_baixa_estoque_sessao

        hoje = timezone.localdate()
        protocolo = Protocolo.objects.create(clinica=self.clinica, nome="Protocolo Teste")
        ItemProtocolo.objects.create(
            protocolo=protocolo,
            apresentacao=self.apresentacao,
            ciclos="1",
            dias_ciclo="1",
            tipo_dose=ItemProtocolo.TipoDose.FIXA,
            dose_valor=Decimal("200"),
        )
        paciente = Paciente.objects.create(
            clinica=self.clinica,
            nome="Paciente Teste",
            data_inicio=hoje,
            protocolo=protocolo,
        )
        lote = Lote.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            numero_lote="LOT-003",
            data_validade=hoje + timedelta(days=60),
            quantidade_inicial=10,
            quantidade_atual=10,
        )
        sessao = SessaoTratamento.objects.create(
            clinica=self.clinica,
            paciente=paciente,
            protocolo=protocolo,
            data_hora=timezone.now(),
            ciclo=1,
            dia_ciclo=1,
            status=SessaoTratamento.Status.REALIZADA,
        )

        ok, msgs = processar_baixa_estoque_sessao(sessao)
        self.assertTrue(ok)
        lote.refresh_from_db()
        self.assertEqual(lote.quantidade_atual, 8)  # 200mg / 100mg per frasco = 2 frascos baixados

