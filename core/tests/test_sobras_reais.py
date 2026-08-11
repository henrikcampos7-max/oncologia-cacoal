from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Apresentacao,
    Clinica,
    ItemProtocolo,
    Lote,
    Medicamento,
    Paciente,
    PerfilUsuario,
    Protocolo,
    SessaoTratamento,
    SobraReal,
)
from core.services import calcular_previsao_sobras, processar_baixa_estoque_sessao, sobras_reais_validas


class SobraRealModelTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Clínica Sobras")
        self.medicamento = Medicamento.objects.create(
            clinica=self.clinica, nome="Medicamento Y", principio_ativo="Ativo Y"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="10 mg/mL",
            descricao="Frasco 500 mg",
            quantidade_mg=Decimal("500"),
            estabilidade_apos_abertura=Decimal("24"),
            unidade_estabilidade=Apresentacao.UnidadeEstabilidade.HORAS,
        )
        self.paciente = Paciente.objects.create(
            clinica=self.clinica, nome="Paciente Origem", data_inicio=timezone.localdate()
        )
        self.sobra = SobraReal.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            quantidade_mg=Decimal("300"),
            paciente_origem=self.paciente,
            data_abertura=timezone.now(),
            limite_estabilidade=timezone.now() + timedelta(hours=20),
        )

    def test_status_inicial_e_propriedade_estabilidade(self):
        self.assertEqual(self.sobra.status, SobraReal.Status.DISPONIVEL)
        self.assertTrue(self.sobra.dentro_da_estabilidade)
        self.assertEqual(
            self.sobra.__str__(),
            "Medicamento Y — Frasco 500 mg — 300 mg (Disponível)",
        )

    def test_reutilizar_marca_status_e_paciente(self):
        destino = Paciente.objects.create(
            clinica=self.clinica, nome="Paciente Destino", data_inicio=timezone.localdate()
        )
        self.sobra.reutilizar(destino, None)
        self.sobra.refresh_from_db()
        self.assertEqual(self.sobra.status, SobraReal.Status.REUTILIZADA)
        self.assertEqual(self.sobra.paciente_destino, destino)
        self.assertIsNotNone(self.sobra.data_reutilizacao)

    def test_reutilizar_fora_da_estabilidade_falha(self):
        self.sobra.limite_estabilidade = timezone.now() - timedelta(hours=1)
        self.sobra.save(update_fields=["limite_estabilidade"])
        with self.assertRaises(ValueError):
            self.sobra.reutilizar(self.paciente, None)

    def test_descartar(self):
        self.sobra.descartar("Sobrou pouco volume", None)
        self.sobra.refresh_from_db()
        self.assertEqual(self.sobra.status, SobraReal.Status.DESCARTADA)
        self.assertEqual(self.sobra.motivo_descarte, "Sobrou pouco volume")
        self.assertIsNotNone(self.sobra.data_descarte)

    def test_sobras_reais_validas_filtra(self):
        expirada = SobraReal.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            quantidade_mg=Decimal("50"),
            data_abertura=timezone.now() - timedelta(hours=30),
            limite_estabilidade=timezone.now() - timedelta(hours=6),
        )
        validas = sobras_reais_validas(self.clinica)
        self.assertEqual([s.pk for s in validas], [self.sobra.pk])
        self.assertNotIn(expirada, validas)


class SobraViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="farmaceutico", password="senha123", email="f@teste.com"
        )
        self.clinica = Clinica.objects.create(nome="Clínica Sobras View")
        PerfilUsuario.objects.create(
            usuario=self.user,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.FARMACEUTICO,
        )
        self.client.login(username="farmaceutico", password="senha123")
        self.medicamento = Medicamento.objects.create(
            clinica=self.clinica, nome="Medicamento Z", principio_ativo="Ativo Z"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="10 mg/mL",
            descricao="Frasco 500 mg",
            quantidade_mg=Decimal("500"),
            estabilidade_apos_abertura=Decimal("24"),
            unidade_estabilidade=Apresentacao.UnidadeEstabilidade.HORAS,
        )
        self.paciente = Paciente.objects.create(
            clinica=self.clinica, nome="Paciente A", data_inicio=timezone.localdate()
        )

    def test_pagina_sobras_carrega(self):
        resposta = self.client.get(reverse("sobras"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Registrar sobra real")

    def test_registrar_sobra_calcula_limite_estabilidade(self):
        resposta = self.client.post(
            reverse("sobras"),
            {
                "registrar_sobra": "1",
                "apresentacao": self.apresentacao.pk,
                "quantidade_mg": "120",
                "lote": "",
                "paciente_origem": self.paciente.pk,
                "data_abertura": "2026-08-11T08:00",
                "condicoes_armazenamento": "Geladeira 2–8 °C",
            },
        )
        self.assertRedirects(resposta, reverse("sobras"))
        sobra = SobraReal.objects.get()
        self.assertEqual(sobra.quantidade_mg, Decimal("120"))
        self.assertEqual(sobra.clinica, self.clinica)
        self.assertEqual(sobra.criada_por, self.user)
        self.assertIsNotNone(sobra.limite_estabilidade)
        self.assertEqual(
            sobra.limite_estabilidade,
            sobra.apresentacao.limite_estabilidade_desde(sobra.data_abertura),
        )

    def test_reutilizar_e_descartar_pela_view(self):
        sobra = SobraReal.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            quantidade_mg=Decimal("200"),
            data_abertura=timezone.now(),
            limite_estabilidade=timezone.now() + timedelta(hours=12),
        )
        resposta = self.client.post(
            reverse("sobras"),
            {"reutilizar_sobra": "1", "sobra_id": sobra.pk, "paciente_destino": self.paciente.pk},
        )
        self.assertRedirects(resposta, reverse("sobras"))
        sobra.refresh_from_db()
        self.assertEqual(sobra.status, SobraReal.Status.REUTILIZADA)
        self.assertEqual(sobra.paciente_destino, self.paciente)

        outra = SobraReal.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            quantidade_mg=Decimal("80"),
            data_abertura=timezone.now(),
            limite_estabilidade=timezone.now() + timedelta(hours=12),
        )
        resposta = self.client.post(
            reverse("sobras"),
            {"descartar_sobra": "1", "sobra_id": outra.pk, "motivo_descarte": "Teste"},
        )
        self.assertRedirects(resposta, reverse("sobras"))
        outra.refresh_from_db()
        self.assertEqual(outra.status, SobraReal.Status.DESCARTADA)

    def test_motor_consome_sobras_reais_validas(self):
        from datetime import datetime

        from core.models import ItemProtocolo, Protocolo, SessaoTratamento

        SobraReal.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            quantidade_mg=Decimal("500"),
            data_abertura=timezone.now(),
            limite_estabilidade=timezone.now() + timedelta(days=7),
        )
        paciente = Paciente.objects.create(
            clinica=self.clinica, nome="Paciente B", data_inicio=timezone.localdate()
        )
        protocolo = Protocolo.objects.create(clinica=self.clinica, nome="Proto B")
        ItemProtocolo.objects.create(
            protocolo=protocolo,
            apresentacao=self.apresentacao,
            dose_valor=Decimal("300"),
            tipo_dose=ItemProtocolo.TipoDose.FIXA,
        )
        SessaoTratamento.objects.create(
            clinica=self.clinica,
            paciente=paciente,
            protocolo=protocolo,
            data_hora=timezone.make_aware(
                datetime.combine(timezone.localdate() + timedelta(days=1), datetime.min.time().replace(hour=9))
            ),
            ciclo=1,
            dia_ciclo=1,
            status=SessaoTratamento.Status.AGENDADA,
        )
        resultado = calcular_previsao_sobras(self.clinica)
        linha = resultado["apresentacoes"][0]
        self.assertEqual(linha["sobras_iniciais_mg"], Decimal("500"))
        self.assertEqual(linha["frascos_necessarios"], 0)
        self.assertEqual(linha["quantidade_reaproveitada_mg"], Decimal("300"))


class BaixaSessaoGeraSobraTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Clínica Baixa Sobra")
        self.usuario = get_user_model().objects.create_user(
            username="enfermeiro", password="senha123", email="e@teste.com"
        )
        self.medicamento = Medicamento.objects.create(
            clinica=self.clinica, nome="Medicamento B", principio_ativo="Ativo B"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="10 mg/mL",
            descricao="Frasco 500 mg",
            quantidade_mg=Decimal("500"),
            estabilidade_apos_abertura=Decimal("24"),
            unidade_estabilidade=Apresentacao.UnidadeEstabilidade.HORAS,
        )
        self.lote = Lote.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            numero_lote="LOT-SOBRA",
            data_validade=timezone.localdate() + timedelta(days=90),
            quantidade_inicial=10,
            quantidade_atual=10,
        )
        self.protocolo = Protocolo.objects.create(clinica=self.clinica, nome="Proto Baixa")
        ItemProtocolo.objects.create(
            protocolo=self.protocolo,
            apresentacao=self.apresentacao,
            ciclos="1",
            dias_ciclo="1",
            tipo_dose=ItemProtocolo.TipoDose.FIXA,
            dose_valor=Decimal("300"),
        )
        self.paciente = Paciente.objects.create(
            clinica=self.clinica,
            nome="Paciente Baixa",
            data_inicio=timezone.localdate(),
            protocolo=self.protocolo,
        )
        self.sessao = SessaoTratamento.objects.create(
            clinica=self.clinica,
            paciente=self.paciente,
            protocolo=self.protocolo,
            data_hora=timezone.make_aware(
                datetime.combine(timezone.localdate(), datetime.min.time().replace(hour=8))
            ),
            ciclo=1,
            dia_ciclo=1,
            status=SessaoTratamento.Status.REALIZADA,
        )

    def test_baixa_registra_sobra_automaticamente(self):
        ok, msgs = processar_baixa_estoque_sessao(self.sessao, usuario=self.usuario)
        self.assertTrue(ok)
        sobra = SobraReal.objects.get()
        self.assertEqual(sobra.apresentacao, self.apresentacao)
        self.assertEqual(sobra.quantidade_mg, Decimal("200"))  # 500 - 300
        self.assertEqual(sobra.paciente_origem, self.paciente)
        self.assertEqual(sobra.lote, self.lote)
        self.assertEqual(sobra.criada_por, self.usuario)
        self.assertEqual(sobra.status, SobraReal.Status.DISPONIVEL)
        self.assertTrue(sobra.dentro_da_estabilidade)
        self.assertIn("Sobra de 200 mg", " ".join(msgs))

    def test_baixa_sem_estabilidade_nao_cria_sobra(self):
        sem_estabilidade = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="10 mg/mL",
            descricao="Frasco 500 mg sem estabilidade",
            quantidade_mg=Decimal("500"),
            estabilidade_apos_abertura=None,
        )
        ItemProtocolo.objects.create(
            protocolo=self.protocolo,
            apresentacao=sem_estabilidade,
            ciclos="1",
            dias_ciclo="1",
            tipo_dose=ItemProtocolo.TipoDose.FIXA,
            dose_valor=Decimal("300"),
        )
        lote2 = Lote.objects.create(
            clinica=self.clinica,
            apresentacao=sem_estabilidade,
            numero_lote="LOT-SEM-EST",
            data_validade=timezone.localdate() + timedelta(days=90),
            quantidade_inicial=5,
            quantidade_atual=5,
        )
        outra_sessao = SessaoTratamento.objects.create(
            clinica=self.clinica,
            paciente=self.paciente,
            protocolo=self.protocolo,
            data_hora=timezone.make_aware(
                datetime.combine(timezone.localdate(), datetime.min.time().replace(hour=10))
            ),
            ciclo=1,
            dia_ciclo=1,
            status=SessaoTratamento.Status.REALIZADA,
        )
        ok, msgs_debug = processar_baixa_estoque_sessao(outra_sessao)
        lote2.refresh_from_db()
        self.assertTrue(ok, msgs_debug)
        self.assertEqual(SobraReal.objects.count(), 1, msgs_debug)
        self.assertEqual(SobraReal.objects.get().apresentacao, self.apresentacao)
        self.assertEqual(lote2.quantidade_atual, 4, msgs_debug)
