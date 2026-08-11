import os
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.models import (
    AliasMedicamento,
    Apresentacao,
    Clinica,
    ImportacaoArquivo,
    ItemTransferencia,
    Medicamento,
    Transferencia,
)
from core.relatorio_pdf import (
    calcular_hash,
    extrair_relatorio,
    reconhecer_itens,
    resolver_descricao,
)
from core.services import importar_transferencia_pdf

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _texto_pdf(linhas):
    """Codifica linhas como conteúdo de uma página PDF (fonte Helvetica)."""
    linhas_pdf = []
    for indice, linha in enumerate(linhas):
        texto = linha.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if indice == 0:
            linhas_pdf.append(f"BT /F1 12 Tf 72 720 Td ({texto}) Tj")
        else:
            linhas_pdf.append(f"0 -14 Td ({texto}) Tj")
    linhas_pdf.append("ET")
    return ("\n".join(linhas_pdf)).encode("latin-1")


def montar_pdf(*linhas):
    """Gera um PDF 1.4 válido cujo conteúdo textual são as linhas informadas."""
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    ]
    conteudo = _texto_pdf(linhas)
    objetos.append(
        b"<< /Length " + str(len(conteudo)).encode() + b" >>\nstream\n"
        + conteudo
        + b"endstream"
    )
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    cabecalho = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    corpo = []
    for numero, obj in enumerate(objetos, start=1):
        corpo.append(f"{numero} 0 obj\n".encode() + obj + b"\nendobj\n")
    offsets = []
    posicao = len(cabecalho)
    for bloco in corpo:
        offsets.append(posicao)
        posicao += len(bloco)
    xref_offset = posicao
    xref = f"xref\n0 {len(objetos)+1}\n".encode()
    xref += b"0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()
    trailer = (
        f"trailer\n<< /Size {len(objetos)+1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    ).encode()
    return cabecalho + b"".join(corpo) + xref + trailer


def montar_pdf_relatorio_real():
    """Reproduz a estrutura do relatório real 'Transferência entre Estoques'."""
    return montar_pdf(
        "UNIMEDJPR 02/07/2026 10:46",
        "Transferência entre Estoques Página 1 de 1",
        "Origem: UNIMED CENTRO RONDÔNIA - Estoque: Estoque Ji-Parana",
        "Destino: Cacoal - Estoque: Estoque Principal Cacoal",
        "Descrição Lote Qtde Vl. Médio",
        "Tipo de Insumo: Material de Enfermagem",
        "29,0000 2,3762LUVA CIRURGICA ESTERIL 7,0 250302PF",
        "Tipo de Insumo: Medicamento",
        "24,0000 25,6440DIFENIDRIN 50 MG/ML  DIFENIDRIN 50 MG/ML SOL INJ CX 25 AMP VD AMB X 1 M50034585",
        "10,0000 16,7457FAULDFLUOR 50 MG/ML 10 ML FAULDFLUOR 50 MG/ML SOL INJ CT 5 FA VD INC X ",
        "10 ML",
        "24l0388",
        "40,0000 0,1699PREDINISONA 5 MG COM CT BL AL PLAS INC X 20 PREDINISONA 5 MG COM CT BL ",
        "AL PLAS INC X 20",
        "B25C0767",
        "Tipo de Insumo: Solução",
        "3,0000 8,4650ALCOOL 70% 1 LITRO ALCOOL 70% 1 LITRO P25060006",
        "by InterProcess",
    )


def ler_fixture_real():
    caminho = os.path.join(FIXTURE_DIR, "transferencia_jiparana_02-07.pdf")
    with open(caminho, "rb") as arquivo:
        return arquivo.read()


class RelatorioPdfTests(TestCase):
    def setUp(self):
        self.jiparana = Clinica.objects.create(nome="Ji-Paraná")
        self.cacoal = Clinica.objects.create(nome="Cacoal")
        self.user = get_user_model().objects.create_user(
            username="relatorio", password="Password123456789!"
        )
        self.medicamento = Medicamento.objects.create(
            clinica=self.cacoal, nome="Paclitaxel", principio_ativo="Paclitaxel"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="6 mg/mL",
            descricao="Frasco 300 mg",
            quantidade_mg=300,
        )

    def test_extrai_itens_qtd_lote_nome_tipo(self):
        dados = extrair_relatorio(montar_pdf_relatorio_real())
        self.assertEqual(len(dados["itens"]), 5)
        primeiro = dados["itens"][0]
        self.assertEqual(primeiro["quantidade"], 29)
        self.assertEqual(primeiro["lote"], "250302PF")
        self.assertEqual(primeiro["nome"], "LUVA CIRURGICA ESTERIL 7,0")
        self.assertEqual(primeiro["tipo_insumo"], "Material de Enfermagem")

    def test_descricao_duplicada_e_limpa(self):
        dados = extrair_relatorio(montar_pdf_relatorio_real())
        difenidrin = dados["itens"][1]
        self.assertEqual(difenidrin["nome"], "DIFENIDRIN 50 MG/ML")
        self.assertEqual(difenidrin["lote"], "M50034585")
        self.assertEqual(difenidrin["quantidade"], 24)

    def test_lote_quebrado_na_linha_seguinte(self):
        dados = extrair_relatorio(montar_pdf_relatorio_real())
        fauldf = next(i for i in dados["itens"] if "FAULDFLUOR" in i["nome"])
        self.assertEqual(fauldf["lote"], "24l0388")
        self.assertEqual(fauldf["quantidade"], 10)
        self.assertTrue(fauldf["nome"].startswith("FAULDFLUOR 50 MG/ML"))

    def test_data_emissao_e_referencia_destino(self):
        dados = extrair_relatorio(montar_pdf_relatorio_real())
        self.assertEqual(dados["data_emissao"], date(2026, 7, 2))
        self.assertIn("Cacoal", dados["referencia_externa"])

    def test_linhas_de_moldura_nao_viram_itens(self):
        dados = extrair_relatorio(montar_pdf_relatorio_real())
        todos_nomes = [item["nome"] for item in dados["itens"]]
        self.assertFalse(any("Página" in nome or "InterProcess" in nome for nome in todos_nomes))

    def test_hash_sha256_deterministico(self):
        conteudo = montar_pdf_relatorio_real()
        self.assertEqual(calcular_hash(conteudo), calcular_hash(conteudo))
        outro = montar_pdf("1,0000 2,0000OUTRO ITEM LOTE-1")
        self.assertNotEqual(calcular_hash(conteudo), calcular_hash(outro))

    def test_pdf_vazio_levanta_erro(self):
        with self.assertRaises(ValueError):
            extrair_relatorio(b"")

    def test_pdf_sem_itens_levanta_erro(self):
        with self.assertRaises(ValueError):
            extrair_relatorio(montar_pdf("Texto sem itens reconhecíveis"))


class RelatorioRealFixtureTests(TestCase):
    """Validação contra o relatório real de Ji-Paraná (TRANSF 02-07)."""

    def test_fixture_real_extrai_16_itens(self):
        dados = extrair_relatorio(ler_fixture_real())
        self.assertEqual(len(dados["itens"]), 16)
        self.assertEqual(dados["data_emissao"], date(2026, 7, 2))
        self.assertIn("Destino: Cacoal", dados["referencia_externa"])

    def test_fixture_real_itens_medicamento(self):
        dados = extrair_relatorio(ler_fixture_real())
        medicamentos = [
            i for i in dados["itens"] if i["tipo_insumo"] == "Medicamento"
        ]
        self.assertEqual(len(medicamentos), 11)
        por_nome = {i["nome"]: i for i in dados["itens"]}
        keytruda = por_nome["KEYTRUDA 100 MG"]
        self.assertEqual(keytruda["quantidade"], 4)
        self.assertEqual(keytruda["lote"], "Z013424")
        glivec = por_nome["GLIVEC 400 MG COM REV CT BL AL/AL X 30"]
        self.assertEqual(glivec["quantidade"], 30)
        self.assertEqual(glivec["lote"], "PL1078")

    def test_fixture_real_sem_lote_em_nenhum_item(self):
        dados = extrair_relatorio(ler_fixture_real())
        self.assertTrue(all(i["lote"] for i in dados["itens"]))


class ResolucaoDescricaoTests(TestCase):
    def setUp(self):
        self.cacoal = Clinica.objects.create(nome="Cacoal")
        self.medicamento = Medicamento.objects.create(
            clinica=self.cacoal, nome="Oxaliplatina", principio_ativo="Oxaliplatina"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="5 mg/mL",
            descricao="Frasco 100 mg",
            quantidade_mg=100,
        )

    def test_resolve_por_nome_do_medicamento(self):
        apresentacao, medicamento, via_alias = resolver_descricao(
            self.cacoal, "Oxaliplatina 100 mg"
        )
        self.assertEqual(apresentacao, self.apresentacao)
        self.assertEqual(medicamento, self.medicamento)
        self.assertFalse(via_alias)

    def test_resolve_por_alias_aprovado(self):
        AliasMedicamento.objects.create(
            clinica=self.cacoal,
            alias="OXALI 5mg/mL FR 100MG",
            medicamento=self.medicamento,
        )
        apresentacao, medicamento, via_alias = resolver_descricao(
            self.cacoal, "OXALI 5mg/mL FR 100MG"
        )
        self.assertEqual(apresentacao, self.apresentacao)
        self.assertTrue(via_alias)

    def test_desconhecido_nao_resolve(self):
        apresentacao, medicamento, via_alias = resolver_descricao(
            self.cacoal, "Inexistente 999 mg"
        )
        self.assertIsNone(apresentacao)
        self.assertIsNone(medicamento)
        self.assertFalse(via_alias)

    def test_reconhecer_itens_separa_conhecidos(self):
        itens = [
            {"quantidade": 2, "nome": "Oxaliplatina 100 mg", "lote": "L1", "tipo_insumo": ""},
            {"quantidade": 1, "nome": "Inexistente 999 mg", "lote": "L2", "tipo_insumo": ""},
        ]
        reconhecidos, nao_reconhecidos = reconhecer_itens(self.cacoal, itens)
        self.assertEqual(len(reconhecidos), 1)
        self.assertEqual(reconhecidos[0]["quantidade"], 2)
        self.assertEqual(reconhecidos[0]["lote"], "L1")
        self.assertEqual(len(nao_reconhecidos), 1)


class ImportarTransferenciaPdfTests(TestCase):
    def setUp(self):
        self.jiparana = Clinica.objects.create(nome="Ji-Paraná")
        self.cacoal = Clinica.objects.create(nome="Cacoal")
        self.user = get_user_model().objects.create_user(
            username="importpdf", password="Password123456789!"
        )
        self.medicamento = Medicamento.objects.create(
            clinica=self.cacoal, nome="Gencitabina", principio_ativo="Gencitabina"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="38 mg/mL",
            descricao="Frasco 1000 mg",
            quantidade_mg=1000,
        )

    def _arquivo(self):
        return SimpleUploadedFile(
            "relatorio.pdf",
            montar_pdf(
                "UNIMEDJPR 15/12/2026 09:00",
                "Destino: Cacoal - Estoque: Estoque Principal Cacoal",
                "Tipo de Insumo: Medicamento",
                "10,0000 5,0000GENCITABINA 1000 MG GENCITABINA 1000 MG LOTEGEM1",
            ),
            content_type="application/pdf",
        )

    def test_importa_transferencia_com_lote_esperado(self):
        arquivo = self._arquivo()
        transferencia, reconhecidos, erros = importar_transferencia_pdf(
            self.jiparana, self.cacoal, arquivo, usuario=self.user
        )
        self.assertIsNotNone(transferencia)
        self.assertEqual(len(reconhecidos), 1)
        self.assertEqual(
            transferencia.status_conferencia,
            Transferencia.StatusConferencia.RELATORIO_IMPORTADO,
        )
        item = ItemTransferencia.objects.get(transferencia=transferencia)
        self.assertEqual(item.apresentacao, self.apresentacao)
        self.assertEqual(item.quantidade, 10)
        self.assertEqual(item.lote_esperado, "LOTEGEM1")
        self.assertEqual(item.tipo_insumo, "Medicamento")
        self.assertEqual(transferencia.data_relatorio, date(2026, 12, 15))

    def test_duplicidade_por_hash_e_rejeitada(self):
        importar_transferencia_pdf(self.jiparana, self.cacoal, self._arquivo(), usuario=self.user)
        transferencia, reconhecidos, erros = importar_transferencia_pdf(
            self.jiparana, self.cacoal, self._arquivo(), usuario=self.user
        )
        self.assertIsNone(transferencia)
        self.assertTrue(any("hash duplicado" in erro for erro in erros))
        self.assertEqual(Transferencia.objects.count(), 1)

    def test_item_nao_reconhecido_nao_bloqueia(self):
        arquivo = SimpleUploadedFile(
            "relatorio.pdf",
            montar_pdf(
                "1,0000 2,0000MEDICAMENTO DESCONHECIDO 500 MG LOTE-X",
            ),
            content_type="application/pdf",
        )
        transferencia, reconhecidos, erros = importar_transferencia_pdf(
            self.jiparana, self.cacoal, arquivo, usuario=self.user
        )
        self.assertIsNotNone(transferencia)
        self.assertEqual(reconhecidos, [])
        self.assertTrue(any("não reconhecido" in erro for erro in erros))
        self.assertEqual(ItemTransferencia.objects.filter(transferencia=transferencia).count(), 0)

    def test_registra_importacao_na_auditoria_de_arquivos(self):
        importar_transferencia_pdf(self.jiparana, self.cacoal, self._arquivo(), usuario=self.user)
        registro = ImportacaoArquivo.objects.get(tipo=ImportacaoArquivo.Tipo.TRANSFERENCIAS)
        self.assertEqual(registro.importadas, 1)
        self.assertEqual(registro.clinica, self.cacoal)