from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.models import (
    Apresentacao,
    Clinica,
    ItemProtocolo,
    Lote,
    Medicamento,
    MovimentacaoEstoque,
    Paciente,
    Protocolo,
    SessaoTratamento,
)
from core.services import calcular_previsao_sobras, calcular_sugestao_compras


class MotorSobrasProjetadasTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Clínica Motor")
        self.medicamento = Medicamento.objects.create(
            clinica=self.clinica, nome="Medicamento X", principio_ativo="Ativo X"
        )

    def criar_apresentacao(self, quantidade_mg=500, estabilidade_horas=24):
        return Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="10 mg/mL",
            descricao=f"Frasco {quantidade_mg} mg",
            quantidade_mg=Decimal(str(quantidade_mg)),
            estabilidade_apos_abertura=Decimal(str(estabilidade_horas))
            if estabilidade_horas is not None
            else None,
        )

    def criar_administracao(self, nome_paciente, dose_mg, dia, hora, apresentacao):
        paciente = Paciente.objects.create(
            clinica=self.clinica,
            nome=nome_paciente,
            data_inicio=timezone.localdate(),
        )
        protocolo = Protocolo.objects.create(clinica=self.clinica, nome=f"Proto {nome_paciente}")
        ItemProtocolo.objects.create(
            protocolo=protocolo,
            apresentacao=apresentacao,
            dose_valor=Decimal(str(dose_mg)),
            tipo_dose=ItemProtocolo.TipoDose.FIXA,
        )
        base = timezone.localdate() + timedelta(days=dia)
        return SessaoTratamento.objects.create(
            clinica=self.clinica,
            paciente=paciente,
            protocolo=protocolo,
            data_hora=timezone.make_aware(datetime.combine(base, datetime.min.time().replace(hour=hora))),
            ciclo=1,
            dia_ciclo=1,
            status=SessaoTratamento.Status.AGENDADA,
        )

    def executar_motor(self, apresentacao):
        resultado = calcular_previsao_sobras(self.clinica)
        linha = next(
            p for p in resultado["apresentacoes"] if p["apresentacao_id"] == apresentacao.pk
        )
        return linha

    def test_exemplo_obrigatorio_quatro_pacientes(self):
        ap = self.criar_apresentacao()
        self.criar_administracao("Paciente A", 350, 0, 8, ap)
        self.criar_administracao("Paciente B", 100, 0, 16, ap)
        self.criar_administracao("Paciente C", 300, 1, 7, ap)
        self.criar_administracao("Paciente D", 100, 2, 10, ap)

        linha = self.executar_motor(ap)

        self.assertEqual(linha["frascos_sem_reaproveitamento"], 4)
        self.assertEqual(linha["frascos_com_reaproveitamento"], 3)
        self.assertEqual(linha["economia_frascos"], 1)
        self.assertEqual(linha["quantidade_reaproveitada_mg"], Decimal("150.00"))
        self.assertEqual(linha["perda_projetada_mg"], Decimal("250.00"))

        aberturas = [e for e in linha["eventos"] if e["tipo"] == "abertura"]
        reusos = [e for e in linha["eventos"] if e["tipo"] == "reuso"]
        perdas = [e for e in linha["eventos"] if e["tipo"] == "perda_projetada"]

        self.assertEqual([e["paciente"] for e in aberturas], ["Paciente A", "Paciente C", "Paciente D"])
        self.assertEqual([e["mg"] for e in aberturas], [350, 250, 100])
        self.assertEqual([(e["paciente"], e["mg"]) for e in reusos], [("Paciente B", 100), ("Paciente C", 50)])
        self.assertEqual(len(perdas), 1)
        self.assertEqual(perdas[0]["mg"], 250)
        self.assertEqual(perdas[0]["paciente"], "Paciente C")

    def test_sobra_suficiente_para_paciente_seguinte(self):
        ap = self.criar_apresentacao()
        self.criar_administracao("Paciente A", 350, 0, 8, ap)
        self.criar_administracao("Paciente B", 100, 0, 16, ap)

        linha = self.executar_motor(ap)
        self.assertEqual(linha["frascos_com_reaproveitamento"], 1)
        self.assertEqual(linha["frascos_sem_reaproveitamento"], 2)
        reusos = [e for e in linha["eventos"] if e["tipo"] == "reuso"]
        self.assertEqual([(e["paciente"], e["mg"]) for e in reusos], [("Paciente B", 100)])

    def test_sobra_parcialmente_suficiente(self):
        ap = self.criar_apresentacao()
        self.criar_administracao("Paciente A", 350, 0, 8, ap)
        self.criar_administracao("Paciente B", 180, 0, 16, ap)

        linha = self.executar_motor(ap)
        self.assertEqual(linha["frascos_com_reaproveitamento"], 2)
        self.assertEqual(linha["quantidade_reaproveitada_mg"], Decimal("150.00"))
        aberturas = [e for e in linha["eventos"] if e["tipo"] == "abertura"]
        self.assertEqual(aberturas[-1]["paciente"], "Paciente B")
        self.assertEqual(aberturas[-1]["mg"], 30)

    def test_paciente_fora_da_estabilidade_nao_reutiliza(self):
        ap = self.criar_apresentacao(estabilidade_horas=24)
        self.criar_administracao("Paciente A", 350, 0, 8, ap)
        self.criar_administracao("Paciente B", 100, 2, 10, ap)

        linha = self.executar_motor(ap)
        self.assertEqual(linha["frascos_com_reaproveitamento"], 2)
        self.assertEqual(linha["quantidade_reaproveitada_mg"], Decimal("0.00"))
        self.assertEqual(linha["perda_projetada_mg"], Decimal("150.00"))
        perdas = [e for e in linha["eventos"] if e["tipo"] == "perda_projetada"]
        self.assertEqual(len(perdas), 1)
        self.assertEqual(perdas[0]["mg"], 150)

    def test_varios_pacientes_dentro_da_estabilidade_um_frasco(self):
        ap = self.criar_apresentacao()
        self.criar_administracao("Paciente A", 200, 0, 8, ap)
        self.criar_administracao("Paciente B", 100, 0, 12, ap)
        self.criar_administracao("Paciente C", 150, 0, 16, ap)
        self.criar_administracao("Paciente D", 50, 1, 7, ap)

        linha = self.executar_motor(ap)
        self.assertEqual(linha["frascos_com_reaproveitamento"], 1)
        self.assertEqual(linha["frascos_sem_reaproveitamento"], 4)
        self.assertEqual(linha["quantidade_reaproveitada_mg"], Decimal("300.00"))

    def test_fefo_prioriza_sobra_que_vence_primeiro(self):
        from core.services import _simular_reaproveitamento

        ap = self.criar_apresentacao()
        sessao = self.criar_administracao("Paciente C", 150, 0, 8, ap)
        agora = sessao.data_hora - timedelta(hours=5)
        sobras_iniciais = [
            {"restante_mg": Decimal("100"), "limite": agora + timedelta(hours=10), "origem": "Paciente A"},
            {"restante_mg": Decimal("200"), "limite": agora + timedelta(hours=20), "origem": "Paciente B"},
        ]
        administracao = {
            "sessao_id": sessao.pk,
            "paciente": sessao.paciente,
            "data_hora": sessao.data_hora,
            "apresentacao": ap,
            "dose_mg": Decimal("150"),
        }

        linha = _simular_reaproveitamento(ap, [administracao], sobras_iniciais=sobras_iniciais)

        self.assertEqual(linha["frascos_com_reaproveitamento"], 0)
        self.assertEqual(linha["frascos_sem_reaproveitamento"], 1)
        reusos = [e for e in linha["eventos"] if e["tipo"] == "reuso"]
        self.assertEqual(len(reusos), 2)
        self.assertEqual(reusos[0]["mg"], 100)
        self.assertIn("Paciente A", reusos[0]["detalhe"])
        self.assertEqual(reusos[1]["mg"], 50)
        self.assertIn("Paciente B", reusos[1]["detalhe"])

    def test_dose_maior_que_o_frasco_abre_multiplos_frascos(self):
        ap = self.criar_apresentacao()
        self.criar_administracao("Paciente A", 700, 0, 8, ap)
        self.criar_administracao("Paciente B", 500, 0, 12, ap)

        linha = self.executar_motor(ap)
        self.assertEqual(linha["frascos_sem_reaproveitamento"], 3)
        self.assertEqual(linha["frascos_com_reaproveitamento"], 3)
        self.assertEqual(linha["economia_frascos"], 0)
        aberturas = [e for e in linha["eventos"] if e["tipo"] == "abertura"]
        self.assertEqual(aberturas[0]["detalhe"], "2 frasco(s) de 500.000 mg")
        self.assertEqual(linha["quantidade_reaproveitada_mg"], Decimal("300.00"))

    def test_nova_sobra_apos_abertura_atende_paciente_posterior(self):
        ap = self.criar_apresentacao()
        self.criar_administracao("Paciente A", 350, 0, 8, ap)
        self.criar_administracao("Paciente B", 100, 0, 16, ap)
        self.criar_administracao("Paciente C", 300, 1, 6, ap)
        self.criar_administracao("Paciente D", 100, 1, 18, ap)

        linha = self.executar_motor(ap)
        self.assertEqual(linha["frascos_com_reaproveitamento"], 2)
        self.assertEqual(linha["frascos_sem_reaproveitamento"], 4)
        self.assertEqual(linha["quantidade_reaproveitada_mg"], Decimal("250.00"))
        reusos = [e for e in linha["eventos"] if e["tipo"] == "reuso"]
        self.assertEqual(reusos[-1]["paciente"], "Paciente D")
        self.assertIn("Paciente C", reusos[-1]["detalhe"])

    def test_ausencia_de_estabilidade_nao_reaproveita(self):
        ap = self.criar_apresentacao(estabilidade_horas=None)
        self.criar_administracao("Paciente A", 350, 0, 8, ap)
        self.criar_administracao("Paciente B", 100, 0, 16, ap)

        linha = self.executar_motor(ap)
        self.assertEqual(linha["flag"], "ESTABILIDADE_NAO_CADASTRADA")
        self.assertEqual(linha["frascos_com_reaproveitamento"], 2)
        self.assertEqual(linha["frascos_sem_reaproveitamento"], 2)
        self.assertEqual(linha["quantidade_reaproveitada_mg"], Decimal("0.00"))
        self.assertFalse([e for e in linha["eventos"] if e["tipo"] == "reuso"])

    def test_estabilidade_exatamente_no_limite_reutiliza(self):
        ap = self.criar_apresentacao(estabilidade_horas=24)
        self.criar_administracao("Paciente A", 350, 0, 8, ap)
        self.criar_administracao("Paciente B", 100, 1, 8, ap)

        linha = self.executar_motor(ap)
        self.assertEqual(linha["frascos_com_reaproveitamento"], 1)
        self.assertEqual(linha["quantidade_reaproveitada_mg"], Decimal("100.00"))

    def test_previsao_de_compra_usa_reaproveitamento(self):
        ap = self.criar_apresentacao()
        self.criar_administracao("Paciente A", 350, 0, 8, ap)
        self.criar_administracao("Paciente B", 100, 0, 16, ap)
        self.criar_administracao("Paciente C", 300, 1, 7, ap)
        self.criar_administracao("Paciente D", 100, 2, 10, ap)

        sugestoes = calcular_sugestao_compras(self.clinica, margem_seguranca=0)
        sugestao = next(s for s in sugestoes if s["apresentacao"].pk == ap.pk)
        self.assertEqual(sugestao["necessario"], 3)
        self.assertEqual(sugestao["frascos_sem_reaproveitamento"], 4)
        self.assertEqual(sugestao["frascos_com_reaproveitamento"], 3)
        self.assertEqual(sugestao["economia_frascos"], 1)
        self.assertEqual(sugestao["estoque"], 0)
        self.assertEqual(sugestao["sugerido_compra"], 3)

    def test_simulacao_nao_altera_estoque_fisico(self):
        ap = self.criar_apresentacao()
        lote = Lote.objects.create(
            clinica=self.clinica,
            apresentacao=ap,
            numero_lote="LOT-MOTOR",
            data_validade=timezone.localdate() + timedelta(days=200),
            quantidade_inicial=10,
            quantidade_atual=10,
        )
        self.criar_administracao("Paciente A", 350, 0, 8, ap)
        self.criar_administracao("Paciente B", 100, 0, 16, ap)

        calcular_previsao_sobras(self.clinica)

        lote.refresh_from_db()
        self.assertEqual(lote.quantidade_atual, 10)
        self.assertEqual(lote.quantidade_reservada, 0)
        self.assertFalse(MovimentacaoEstoque.objects.exists())

    def test_inconsistencia_sem_dados_de_dose(self):
        ap = self.criar_apresentacao()
        paciente = Paciente.objects.create(
            clinica=self.clinica, nome="Sem Peso", data_inicio=timezone.localdate()
        )
        protocolo = Protocolo.objects.create(clinica=self.clinica, nome="Proto Sem Peso")
        ItemProtocolo.objects.create(
            protocolo=protocolo,
            apresentacao=ap,
            dose_valor=Decimal("5"),
            tipo_dose=ItemProtocolo.TipoDose.MG_KG,
        )
        base = timezone.localdate()
        SessaoTratamento.objects.create(
            clinica=self.clinica,
            paciente=paciente,
            protocolo=protocolo,
            data_hora=timezone.make_aware(datetime.combine(base, datetime.min.time().replace(hour=8))),
            ciclo=1,
            dia_ciclo=1,
        )
        resultado = calcular_previsao_sobras(self.clinica)
        self.assertEqual(len(resultado["inconsistencias"]), 1)
        self.assertEqual(resultado["apresentacoes"], [])
