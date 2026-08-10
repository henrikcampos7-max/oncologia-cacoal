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

