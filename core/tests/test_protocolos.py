from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Apresentacao,
    Clinica,
    ItemProtocolo,
    Medicamento,
    PerfilUsuario,
    Protocolo,
    RegistroAuditoria,
)


class ProtocolosViewTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Clínica Protocolos")
        self.user = get_user_model().objects.create_user(
            username="adminproto", password="Password123456789!"
        )
        self.perfil = PerfilUsuario.objects.create(
            usuario=self.user,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.ADMINISTRADOR,
            ativo=True,
        )
        self.client.login(username="adminproto", password="Password123456789!")
        self.medicamento = Medicamento.objects.create(
            clinica=self.clinica, nome="OncoMed Proto", principio_ativo="Ativo"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="1 mg/mL",
            descricao="Frasco 100 mg",
            quantidade_mg=Decimal("100"),
        )

    def test_lista_protocolos_acessivel(self):
        response = self.client.get(reverse("protocolos"))
        self.assertEqual(response.status_code, 200)

    def test_cria_protocolo_e_redireciona_para_itens(self):
        response = self.client.post(
            reverse("protocolos"),
            {
                "nome": "Protocolo X",
                "diagnostico_referencia": "Neoplasia fictícia",
                "intervalo_dias": 21,
                "total_ciclos": 6,
                "ativo": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        protocolo = Protocolo.objects.get(nome="Protocolo X")
        self.assertEqual(response.url, reverse("editar_protocolo", kwargs={"pk": protocolo.pk}))
        self.assertEqual(protocolo.clinica, self.clinica)
        self.assertTrue(RegistroAuditoria.objects.filter(clinica=self.clinica).exists())

    def test_adiciona_item_ao_protocolo(self):
        protocolo = Protocolo.objects.create(
            clinica=self.clinica, nome="Protocolo Y", intervalo_dias=21, total_ciclos=6
        )
        response = self.client.post(
            reverse("editar_protocolo", kwargs={"pk": protocolo.pk}),
            {
                "salvar_item": "1",
                "item-apresentacao": self.apresentacao.pk,
                "item-ciclos": "1, 2",
                "item-dias_ciclo": "1, 15",
                "item-tipo_dose": ItemProtocolo.TipoDose.MG_M2,
                "item-dose_valor": "5",
            },
        )
        self.assertEqual(response.status_code, 302)
        item = protocolo.itens.get()
        self.assertEqual(item.apresentacao, self.apresentacao)
        self.assertEqual(item.dose_valor, Decimal("5"))
        self.assertTrue(RegistroAuditoria.objects.filter(clinica=self.clinica).exists())

    def test_remove_item_do_protocolo(self):
        protocolo = Protocolo.objects.create(
            clinica=self.clinica, nome="Protocolo Z", intervalo_dias=21, total_ciclos=6
        )
        item = ItemProtocolo.objects.create(
            protocolo=protocolo,
            apresentacao=self.apresentacao,
            ciclos="1",
            dias_ciclo="1",
            tipo_dose=ItemProtocolo.TipoDose.FIXA,
            dose_valor=Decimal("10"),
        )
        response = self.client.post(reverse("remover_item_protocolo", kwargs={"pk": item.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(protocolo.itens.exists())

    def test_perfil_sem_permissao_nao_cria_protocolo(self):
        leitor = get_user_model().objects.create_user(
            username="leitorproto", password="Password123456789!"
        )
        PerfilUsuario.objects.create(
            usuario=leitor,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.LEITURA,
            ativo=True,
        )
        self.client.login(username="leitorproto", password="Password123456789!")
        response = self.client.post(
            reverse("protocolos"),
            {"nome": "Proibido", "intervalo_dias": 21, "total_ciclos": 1},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Protocolo.objects.filter(nome="Proibido").exists())
