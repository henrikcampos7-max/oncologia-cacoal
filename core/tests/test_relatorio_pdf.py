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


def montar_pdf_minimo(*linhas):
    """Gera um PDF 1.4 válido cujo conteúdo textual são as linhas informadas."""
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    ]
    linhas_pdf = []
    for indice, linha in enumerate(linhas):
        texto = linha.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if indice == 0:
            linhas_pdf.append(f"BT /F1 12 Tf 72 720 Td ({texto}) Tj")
        else:
            linhas_pdf.append(f"0 -14 Td ({texto}) Tj")
    linhas_pdf.append("ET")
    conteudo = ("\n".join(linhas_pdf)).encode("latin-1")
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

    def _pdf_completo(self):
        return montar_pdf_minimo(
            "RELATÓRIO DE TRANSFERÊNCIA REV. 77",
            "GUIA CT: 000123456",
            "1) Paclitaxel 300 mg 10/08/2026 LOTE-ABC-01 5",
            "2) Paclitaxel 300 mg 08/2026 LOTE-XYZ-02 3",
            "Prof. Farmacêutico Responsável: Assinatura",
            "Atividade diária registrada em sistema",
        )

    def test_extrai_itens_lote_validade_quantidade(self):
        dados = extrair_relatorio(self._pdf_completo())
        self.assertEqual(len(dados["itens"]), 2)
        primeiro = dados["itens"][0]
        self.assertEqual(primeiro["descricao"], "Paclitaxel 300 mg")
        self.assertEqual(primeiro["lote"], "LOTE-ABC-01")
        self.assertEqual(primeiro["quantidade"], 5)
        self.assertEqual(primeiro["validade"], date(2026, 8, 10))

    def test_validade_mes_ano_aceita(self):
        dados = extrair_relatorio(self._pdf_completo())
        segundo = dados["itens"][1]
        self.assertEqual(segundo["validade"], date(2026, 8, 1))

    def test_cabecalho_nao_vira_divergencia(self):
        dados = extrair_relatorio(self._pdf_completo())
        linhas_nao_reconhecidas = [
            msg for msg in dados["informativo"] if "não reconhecida" in msg
        ]
        self.assertEqual(linhas_nao_reconhecidas, [])

    def test_referencia_externa_e_data_emissao(self):
        dados = extrair_relatorio(self._pdf_completo())
        self.assertEqual(dados["referencia_externa"], "000123456")
        self.assertEqual(dados["data_emissao"], date(2026, 8, 10))

    def test_hash_sha256_deterministico(self):
        conteudo = self._pdf_completo()
        self.assertEqual(calcular_hash(conteudo), calcular_hash(conteudo))
        outro = montar_pdf_minimo("1) Outro Item 01/01/2026 LOTE-Q 2")
        self.assertNotEqual(calcular_hash(conteudo), calcular_hash(outro))

    def test_pdf_vazio_levanta_erro(self):
        with self.assertRaises(ValueError):
            extrair_relatorio(b"")

    def test_pdf_sem_itens_levanta_erro(self):
        with self.assertRaises(ValueError):
            extrair_relatorio(montar_pdf_minimo("Texto sem itens reconhecíveis"))


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
            {"descricao": "Oxaliplatina 100 mg", "lote": "L1", "validade": None, "quantidade": 2},
            {"descricao": "Inexistente 999 mg", "lote": "L2", "validade": None, "quantidade": 1},
        ]
        reconhecidos, nao_reconhecidos = reconhecer_itens(self.cacoal, itens)
        self.assertEqual(len(reconhecidos), 1)
        self.assertEqual(reconhecidos[0]["quantidade"], 2)
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
            montar_pdf_minimo(
                "1) Gencitabina 1000 mg 12/12/2026 LOTE-GEM-1 10",
                "Guia CT: 999888777",
            ),
            content_type="application/pdf",
        )

    def test_importa_transferencia_com_itens(self):
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
        self.assertTrue(transferencia.importada)
        self.assertNotEqual(transferencia.hash_relatorio, "")
        self.assertTrue(transferencia.relatorio_arquivo.name.endswith(".pdf"))
        item = ItemTransferencia.objects.get(transferencia=transferencia)
        self.assertEqual(item.apresentacao, self.apresentacao)
        self.assertEqual(item.quantidade, 10)

    def test_duplicidade_por_hash_e_rejeitada(self):
        arquivo = self._arquivo()
        importar_transferencia_pdf(self.jiparana, self.cacoal, arquivo, usuario=self.user)
        outro_arquivo = self._arquivo()
        transferencia, reconhecidos, erros = importar_transferencia_pdf(
            self.jiparana, self.cacoal, outro_arquivo, usuario=self.user
        )
        self.assertIsNone(transferencia)
        self.assertTrue(any("hash duplicado" in erro for erro in erros))
        self.assertEqual(Transferencia.objects.count(), 1)

    def test_item_nao_reconhecido_nao_bloqueia(self):
        arquivo = SimpleUploadedFile(
            "relatorio.pdf",
            montar_pdf_minimo(
                "1) Medicamento Desconhecido 500 mg 01/01/2027 LOTE-X 2",
                "Guia CT: 111222333",
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
        arquivo = self._arquivo()
        importar_transferencia_pdf(self.jiparana, self.cacoal, arquivo, usuario=self.user)
        registro = ImportacaoArquivo.objects.get(tipo=ImportacaoArquivo.Tipo.TRANSFERENCIAS)
        self.assertEqual(registro.importadas, 1)
        self.assertEqual(registro.clinica, self.cacoal)