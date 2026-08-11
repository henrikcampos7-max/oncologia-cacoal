from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Apresentacao,
    Clinica,
    Lote,
    Medicamento,
    Paciente,
    PerfilUsuario,
    Protocolo,
    SessaoTratamento,
)


class CoreViewsTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Clínica Teste Views")
        self.user = get_user_model().objects.create_user(
            username="testuser", password="Password123456789!"
        )
        self.perfil = PerfilUsuario.objects.create(
            usuario=self.user,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.ADMINISTRADOR,
            ativo=True,
        )
        self.client.login(username="testuser", password="Password123456789!")

    def test_estoque_view_accessible(self):
        response = self.client.get(reverse("estoque"))
        self.assertEqual(response.status_code, 200)

    def test_alertas_view_accessible(self):
        response = self.client.get(reverse("alertas"))
        self.assertEqual(response.status_code, 200)

    def test_compras_view_accessible(self):
        response = self.client.get(reverse("compras"))
        self.assertEqual(response.status_code, 200)

    def test_relatorios_view_accessible(self):
        response = self.client.get(reverse("relatorios"))
        self.assertEqual(response.status_code, 200)

    def test_auditoria_view_accessible(self):
        response = self.client.get(reverse("auditoria"))
        self.assertEqual(response.status_code, 200)

    def test_auditoria_grava_registro_ao_cadastrar_paciente(self):
        from core.models import RegistroAuditoria

        response = self.client.post(
            reverse("pacientes"),
            {
                "nome": "Paciente Auditado",
                "diagnostico": "Diagnóstico teste",
                "data_inicio": timezone.localdate().isoformat(),
                "ciclos_previstos": 6,
            },
        )
        self.assertEqual(response.status_code, 302)
        registro = RegistroAuditoria.objects.filter(clinica=self.clinica).first()
        self.assertIsNotNone(registro)
        self.assertEqual(registro.usuario, self.user)
        self.assertIn("Paciente Auditado", registro.detalhes)
        self.assertIn("Cadastro de paciente", registro.acao)

    def test_auditoria_grava_registro_ao_registrar_movimentacao(self):
        from core.models import MovimentacaoEstoque, RegistroAuditoria

        apresentacao = Apresentacao.objects.create(
            medicamento=Medicamento.objects.create(
                clinica=self.clinica, nome="Med Auditado", principio_ativo="Ativo"
            ),
            concentracao="1 mg/mL",
            descricao="Frasco 10 mg",
            quantidade_mg=Decimal("10"),
        )
        lote = Lote.objects.create(
            clinica=self.clinica,
            apresentacao=apresentacao,
            numero_lote="LOT-AUDIT",
            data_validade=timezone.localdate() + timedelta(days=120),
            quantidade_inicial=10,
            quantidade_atual=10,
        )
        response = self.client.post(
            reverse("estoque"),
            {
                "salvar_movimentacao": "1",
                "mov-lote": lote.pk,
                "mov-tipo": MovimentacaoEstoque.TipoMovimentacao.SAIDA,
                "mov-quantidade": 2,
                "mov-observacao": "Teste de auditoria",
            },
        )
        self.assertEqual(response.status_code, 302)
        registro = RegistroAuditoria.objects.filter(clinica=self.clinica).first()
        self.assertIsNotNone(registro)
        self.assertIn("Movimentação de estoque", registro.acao)

    def test_auditoria_reserva_nao_altera_saldo_fisico(self):
        from core.models import MovimentacaoEstoque, RegistroAuditoria

        apresentacao = Apresentacao.objects.create(
            medicamento=Medicamento.objects.create(
                clinica=self.clinica, nome="Med Reserva", principio_ativo="Ativo"
            ),
            concentracao="1 mg/mL",
            descricao="Frasco 10 mg",
            quantidade_mg=Decimal("10"),
        )
        lote = Lote.objects.create(
            clinica=self.clinica,
            apresentacao=apresentacao,
            numero_lote="LOT-RESV",
            data_validade=timezone.localdate() + timedelta(days=120),
            quantidade_inicial=10,
            quantidade_atual=10,
        )
        response = self.client.post(
            reverse("estoque"),
            {
                "salvar_movimentacao": "1",
                "mov-lote": lote.pk,
                "mov-tipo": MovimentacaoEstoque.TipoMovimentacao.RESERVA,
                "mov-quantidade": 3,
                "mov-observacao": "Reserva via view",
            },
        )
        self.assertEqual(response.status_code, 302)
        lote.refresh_from_db()
        self.assertEqual(lote.quantidade_atual, 10)
        self.assertEqual(lote.quantidade_reservada, 3)
        registro = RegistroAuditoria.objects.filter(clinica=self.clinica).first()
        self.assertIsNotNone(registro)
        self.assertIn("Reserva de estoque", registro.acao)

