from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
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
    RegistroAuditoria,
    SessaoTratamento,
)
from core.services import enviar_alertas_por_email


class AlertasEmailTests(TestCase):
    def setUp(self):
        mail.outbox.clear()
        self.clinica = Clinica.objects.create(nome="Clínica Alertas")
        self.user = get_user_model().objects.create_user(
            username="farma", password="Password123456789!", email="farma@exemplo.com"
        )
        PerfilUsuario.objects.create(
            usuario=self.user,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.FARMACEUTICO,
            ativo=True,
        )
        self.user2 = get_user_model().objects.create_user(
            username="leitura", password="Password123456789!", email="leitura@exemplo.com"
        )
        PerfilUsuario.objects.create(
            usuario=self.user2,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.LEITURA,
            ativo=True,
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=Medicamento.objects.create(
                clinica=self.clinica, nome="Med Alertas", principio_ativo="Ativo"
            ),
            concentracao="1 mg/mL",
            descricao="Frasco 10 mg",
            quantidade_mg=Decimal("10"),
        )

    def criar_lote(self, dias_validade, quantidade=5, minimo=5):
        return Lote.objects.create(
            clinica=self.clinica,
            apresentacao=self.apresentacao,
            numero_lote=f"LOT-{dias_validade}",
            data_validade=timezone.localdate() + timedelta(days=dias_validade),
            quantidade_inicial=quantidade,
            quantidade_atual=quantidade,
            estoque_minimo=minimo,
        )

    def test_envia_email_para_administradores_e_farmaceuticos(self):
        self.criar_lote(dias_validade=10)
        destinatarios, total = enviar_alertas_por_email(self.clinica, usuario=self.user)
        self.assertEqual(total, 2)
        self.assertEqual(destinatarios, 1)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["farma@exemplo.com"])
        self.assertIn("LOT-10", email.body)
        self.assertIn("Validade crítica", email.body)

    def test_sem_alertas_nao_envia_email(self):
        self.criar_lote(dias_validade=200, quantidade=20, minimo=5)
        destinatarios, total = enviar_alertas_por_email(self.clinica, usuario=self.user)
        self.assertEqual((destinatarios, total), (0, 0))
        self.assertEqual(len(mail.outbox), 0)

    def test_email_inclui_estoque_baixo_e_faltas_recentes(self):
        self.criar_lote(dias_validade=200, quantidade=2, minimo=5)
        self.client.login(username="farma", password="Password123456789!")
        protocolo = Protocolo.objects.create(clinica=self.clinica, nome="Protocolo A")
        paciente = Paciente.objects.create(
            clinica=self.clinica, nome="Paciente Faltoso", data_inicio=timezone.localdate()
        )
        for i in range(2):
            SessaoTratamento.objects.create(
                clinica=self.clinica,
                paciente=paciente,
                protocolo=protocolo,
                data_hora=timezone.now() - timedelta(days=5 + i),
                status=SessaoTratamento.Status.FALTOU,
                motivo="Abstenção",
            )
        destinatarios, total = enviar_alertas_por_email(self.clinica, usuario=self.user)
        self.assertGreaterEqual(total, 2)
        email = mail.outbox[0]
        self.assertIn("Estoque baixo", email.body)
        self.assertIn("Paciente Faltoso", email.body)

    def test_botao_na_pagina_de_alertas_envia_e_registra_auditoria(self):
        self.criar_lote(dias_validade=5)
        self.client.login(username="farma", password="Password123456789!")
        response = self.client.post(reverse("alertas"), {"enviar_email": "1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        registro = RegistroAuditoria.objects.filter(clinica=self.clinica).first()
        self.assertIsNotNone(registro)
        self.assertIn("Envio de alertas por email", registro.acao)

    def test_perfil_sem_permissao_nao_envia_email(self):
        self.criar_lote(dias_validade=5)
        self.client.login(username="leitura", password="Password123456789!")
        response = self.client.post(reverse("alertas"), {"enviar_email": "1"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)
