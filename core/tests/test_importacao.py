from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from openpyxl import Workbook

from core.models import (
    Apresentacao,
    Clinica,
    ImportacaoArquivo,
    Medicamento,
    PerfilUsuario,
)


def criar_xlsx(caminho):
    workbook = Workbook()
    planilha = workbook.active
    planilha.title = "Medicamentos"
    planilha.append(["Medicamento", "Princípio Ativo", "Apresentação", "Concentração", "MG"])
    planilha.append(["Doxorrubicina", "Doxorrubicina", "Frasco 50 mg", "2 mg/mL", "50"])
    planilha.append(["Paclitaxel", "Paclitaxel", "Frasco 300 mg", "6 mg/mL", "300"])
    planilha.append(["", "", "Frasco sem nome", "", "10"])
    planilha.append(["Cisplatina", "Cisplatina", "Frasco 100 mg", "1 mg/mL", "invalido"])
    workbook.save(caminho)


class ImportacaoTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Clínica Importação")
        self.user = get_user_model().objects.create_user(
            username="importadmin", password="Password123456789!"
        )
        PerfilUsuario.objects.create(
            usuario=self.user,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.ADMINISTRADOR,
            ativo=True,
        )
        self.client.login(username="importadmin", password="Password123456789!")

    def test_inspecionar_importacao_extrai_abas_colunas_e_previa(self):
        from core.services import inspecionar_importacao

        caminho = self.criar_arquivo_temporario()
        abas = inspecionar_importacao(caminho)
        self.assertEqual(abas[0]["nome"], "Medicamentos")
        self.assertEqual(abas[0]["colunas"], ["Medicamento", "Princípio Ativo", "Apresentação", "Concentração", "MG"])
        self.assertEqual(abas[0]["total_linhas"], 4)

    def test_fluxo_upload_preparar_importar(self):
        caminho = self.criar_arquivo_temporario()
        with open(caminho, "rb") as arquivo:
            response = self.client.post(
                reverse("importacoes"),
                {"enviar_arquivo": "1", "arquivo": arquivo},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("importacao_preparar"))

        response = self.client.post(
            reverse("importacao_preparar"),
            {
                "confirmar_importacao": "1",
                "aba": "Medicamentos",
                "map_nome": "0",
                "map_principio_ativo": "1",
                "map_descricao": "2",
                "map_concentracao": "3",
                "map_quantidade_mg": "4",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2 linha(s) importada(s)")
        medicamento = Medicamento.objects.get(clinica=self.clinica, nome="Doxorrubicina")
        apresentacao = Apresentacao.objects.get(
            medicamento=medicamento, descricao="Frasco 50 mg"
        )
        self.assertEqual(apresentacao.quantidade_mg, Decimal("50"))
        registro = ImportacaoArquivo.objects.get(clinica=self.clinica)
        self.assertEqual(registro.importadas, 2)
        self.assertEqual(registro.com_erro, 2)
        self.client.session.flush()

    def test_importacao_exige_mapeamento_obrigatorio(self):
        caminho = self.criar_arquivo_temporario()
        with open(caminho, "rb") as arquivo:
            self.client.post(
                reverse("importacoes"),
                {"enviar_arquivo": "1", "arquivo": arquivo},
            )
        response = self.client.post(
            reverse("importacao_preparar"),
            {"confirmar_importacao": "1", "aba": "Medicamentos", "map_nome": "0"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Medicamento.objects.exists())
        self.client.session.flush()

    def criar_arquivo_temporario(self):
        import os
        import tempfile

        caminho = os.path.join(tempfile.gettempdir(), "teste_importacao_oncologia.xlsx")
        criar_xlsx(caminho)
        return caminho