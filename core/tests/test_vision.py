from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from core.models import (
    Apresentacao,
    Clinica,
    ExtracaoEvidencia,
    ItemTransferencia,
    Medicamento,
    Transferencia,
    TransferenciaEvidencia,
)
from core.vision import (
    AzureDocumentIntelligenceProvider,
    GoogleVisionProvider,
    ManualProvider,
    MockProvider,
    ProviderFactory,
    _parsear_ocr,
    processar_evidencia,
    registrar_extracao,
    resumo_aprovacao,
)


def _imagem(nome="foto.png", conteudo=b"\x89PNG dados de teste"):
    return SimpleUploadedFile(nome, conteudo, content_type="image/png")


class ProvidersTests(TestCase):
    def test_mock_nao_inventa_lote_quando_ausente(self):
        provider = MockProvider()
        campos = provider.extract_image(b"qualquer")
        self.assertEqual(campos["lote"], "")
        self.assertEqual(campos["validade"], None)
        self.assertEqual(campos["quantidade"], None)
        self.assertTrue(campos["requer_revisao"])
        self.assertEqual(campos["confianca_lote"], 0)

    def test_mock_aceita_dados_assistidos(self):
        provider = MockProvider()
        campos = provider.extract_image(
            b"x",
            dados={
                "nome_produto": "Frasco X",
                "lote": "L123",
                "validade": date(2027, 1, 1),
                "quantidade": "3",
            },
        )
        self.assertEqual(campos["lote"], "L123")
        self.assertEqual(campos["quantidade"], 3)
        self.assertFalse(campos["requer_revisao"])

    def test_manual_provider_normaliza_dados(self):
        provider = ManualProvider()
        campos = provider.extract_image(b"x", dados={"lote": "  ABC1  ", "quantidade": "2"})
        self.assertEqual(campos["lote"], "ABC1")
        self.assertEqual(campos["quantidade"], 2)

    def test_mock_classify_qa(self):
        provider = MockProvider()
        self.assertEqual(provider.classify_qa("NAO APROVADO"), ("nao_aprovado", 1.0))
        self.assertEqual(provider.classify_qa("Aprovada"), ("aprovado", 1.0))
        self.assertEqual(provider.classify_qa("nada"), (None, 0.0))

    def test_factory_seleciona_por_env(self):
        self.assertIsInstance(ProviderFactory.obter_provider("mock"), MockProvider)
        self.assertIsInstance(ProviderFactory.obter_provider("manual"), ManualProvider)
        self.assertIsInstance(
            ProviderFactory.obter_provider("azure"), AzureDocumentIntelligenceProvider
        )
        self.assertIsInstance(
            ProviderFactory.obter_provider("google"), GoogleVisionProvider
        )
        with self.assertRaises(ValueError):
            ProviderFactory.obter_provider("inexistente")


class FakeProxy:
    """Proxy determinístico: devolve respostas pré-programadas sem rede."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def abrir(self, request):
        self.chamadas.append(request.full_url)
        return _FakeResponse(self.respostas.pop(0))

    def ler_json(self, response):
        return response.corpo


class _FakeResponse:
    def __init__(self, corpo):
        self.corpo = corpo
        self.headers = corpo.pop("headers", {}) if isinstance(corpo, dict) else {}

    def read(self):
        import json

        return json.dumps(self.corpo).encode("utf-8")

    def close(self):
        pass


AZURE_CONFIG = {
    "azure": {
        "endpoint": "https://fake.cognitiveservices.azure.com/",
        "chave": "CHAVE-FAKE",
        "api_version": "2024-11-30",
        "modelo": "prebuilt-layout",
    }
}


class AzureProviderTests(TestCase):
    def test_extrai_campos_do_texto_ocr(self):
        proxy = FakeProxy(
            [
                {"headers": {"operation-location": "https://fake/operations/1"}},
                {
                    "status": "succeeded",
                    "content": (
                        "PRODUTO: DIFENIDRIN 50 MG/ML\n"
                        "LOTE: M50034585\n"
                        "VAL: 30/11/2028\n"
                        "QTD: 24"
                    ),
                },
            ]
        )
        with override_settings(TRANSFER_CONFERENCE_CONFIG={**AZURE_CONFIG}):
            provider = AzureDocumentIntelligenceProvider(proxy=proxy)
            campos = provider.extract_image(b"imagem-fake")
        self.assertEqual(campos["nome_produto"], "DIFENIDRIN 50 MG/ML")
        self.assertEqual(campos["lote"], "M50034585")
        self.assertEqual(campos["validade"], "2028-11-30")
        self.assertEqual(campos["quantidade"], 24)
        self.assertFalse(campos["requer_revisao"])
        self.assertEqual(campos["confianca_lote"], 1)
        self.assertEqual(len(proxy.chamadas), 2)

    def test_sem_lote_validade_nao_inventa(self):
        proxy = FakeProxy(
            [
                {"headers": {"operation-location": "https://fake/operations/1"}},
                {"status": "succeeded", "content": "PRODUTO: SEM INFO"},
            ]
        )
        with override_settings(TRANSFER_CONFERENCE_CONFIG={**AZURE_CONFIG}):
            campos = AzureDocumentIntelligenceProvider(proxy=proxy).extract_image(b"x")
        self.assertEqual(campos["lote"], "")
        self.assertIsNone(campos["validade"])
        self.assertTrue(campos["requer_revisao"])

    def test_falha_http_levanta_runtimeerror(self):
        import urllib.error as urlerror

        class ProxyErro:
            def abrir(self, request):
                raise urlerror.HTTPError(
                    "url", 401, "Unauthorized", None, None
                )

            def ler_json(self, response):
                raise AssertionError("não deve ler")

        with override_settings(TRANSFER_CONFERENCE_CONFIG={**AZURE_CONFIG}):
            provider = AzureDocumentIntelligenceProvider(proxy=ProxyErro())
            with self.assertRaises(RuntimeError) as ctx:
                provider.extract_image(b"x")
        self.assertIn("401", str(ctx.exception))

    def test_sem_configuracao_orienta_erro(self):
        with override_settings(
            TRANSFER_CONFERENCE_CONFIG={"azure": {"endpoint": "", "chave": ""}}
        ):
            provider = AzureDocumentIntelligenceProvider(proxy=FakeProxy([]))
            with self.assertRaises(RuntimeError) as ctx:
                provider.extract_image(b"x")
        self.assertIn("TRANSFER_AZURE_ENDPOINT", str(ctx.exception))


class GoogleProviderTests(TestCase):
    def test_extrai_campos_do_texto_ocr(self):
        proxy = FakeProxy(
            [
                {
                    "responses": [
                        {
                            "textAnnotations": [
                                {
                                    "description": (
                                        "PRODUTO: RITUXIMABE 500 MG\n"
                                        "LOTE: RIT-2026\n"
                                        "VAL: 03/2029\n"
                                        "QTDE: 4"
                                    )
                                }
                            ]
                        }
                    ]
                }
            ]
        )
        cfg = {
            "google": {"token": "TOKEN-FAKE", "api_endpoint": "https://fake/annotate"}
        }
        with override_settings(TRANSFER_CONFERENCE_CONFIG=cfg):
            campos = GoogleVisionProvider(proxy=proxy).extract_image(b"imagem-fake")
        self.assertEqual(campos["nome_produto"], "RITUXIMABE 500 MG")
        self.assertEqual(campos["lote"], "RIT-2026")
        self.assertEqual(campos["validade"], "2029-03-01")
        self.assertEqual(campos["quantidade"], 4)
        self.assertFalse(campos["requer_revisao"])
        self.assertEqual(len(proxy.chamadas), 1)

    def test_resposta_com_erro_do_google(self):
        proxy = FakeProxy(
            [
                {
                    "responses": [
                        {
                            "error": {
                                "code": 400,
                                "message": "Image is not valid",
                            }
                        }
                    ]
                }
            ]
        )
        cfg = {
            "google": {"token": "TOKEN-FAKE", "api_endpoint": "https://fake/annotate"}
        }
        with override_settings(TRANSFER_CONFERENCE_CONFIG=cfg):
            with self.assertRaises(RuntimeError) as ctx:
                GoogleVisionProvider(proxy=proxy).extract_image(b"x")
        self.assertIn("Image is not valid", str(ctx.exception))

    def test_sem_token_orienta_erro(self):
        with override_settings(
            TRANSFER_CONFERENCE_CONFIG={"google": {"token": "", "api_endpoint": ""}}
        ):
            with self.assertRaises(RuntimeError) as ctx:
                GoogleVisionProvider(proxy=FakeProxy([])).extract_image(b"x")
        self.assertIn("TRANSFER_GOOGLE_TOKEN", str(ctx.exception))


class ParsearOcrTests(TestCase):
    def test_lote_normalizado(self):
        campos = _parsear_ocr("Lote: 24l0388\nVAL: 30/11/2028")
        self.assertEqual(campos["lote"], "24L0388")
        self.assertEqual(campos["validade"], "2028-11-30")

    def test_lote_invalido_rejeitado(self):
        campos = _parsear_ocr("Lote: !!invalido!!")
        self.assertEqual(campos["lote"], "")

    def test_validade_so_mes_ano(self):
        campos = _parsear_ocr("LOTE: X123\nVAL 03/2029")
        self.assertEqual(campos["validade"], "2029-03-01")

    def test_quantidade_somente_rotulada(self):
        self.assertEqual(_parsear_ocr("24 caixas")["quantidade"], None)
        self.assertEqual(_parsear_ocr("QTD: 24")["quantidade"], 24)


class ResumoAprovacaoTests(TestCase):
    def test_aprovado_com_todos_campos_e_confianca_alta(self):
        campos = {
            "nome_produto": "Frasco X",
            "lote": "L1",
            "validade": date(2027, 1, 1),
            "confianca_produto": 0.99,
            "confianca_lote": 0.98,
            "confianca_validade": 0.97,
        }
        aprovado, motivo = resumo_aprovacao(campos)
        self.assertTrue(aprovado)

    def test_reprovado_por_campo_ausente(self):
        aprovado, motivo = resumo_aprovacao({"nome_produto": "X", "lote": ""})
        self.assertFalse(aprovado)
        self.assertIn("validade", motivo)

    def test_reprovado_por_confianca_baixa(self):
        campos = {
            "nome_produto": "X",
            "lote": "L1",
            "validade": date(2027, 1, 1),
            "confianca_produto": 0.5,
        }
        aprovado, motivo = resumo_aprovacao(campos)
        self.assertFalse(aprovado)
        self.assertIn("confianca", motivo)


class ProcessarEvidenciaTests(TestCase):
    def setUp(self):
        self.origem = Clinica.objects.create(nome="Ji-Paraná")
        self.destino = Clinica.objects.create(nome="Cacoal")
        self.user = get_user_model().objects.create_user(
            username="evidencias", password="Password123456789!"
        )
        self.transferencia = Transferencia.objects.create(
            clinica_origem=self.origem,
            clinica_destino=self.destino,
            numero="TR-EVI-001",
        )
        self.medicamento = Medicamento.objects.create(
            clinica=self.destino, nome="Rituximabe", principio_ativo="Rituximabe"
        )
        self.apresentacao = Apresentacao.objects.create(
            medicamento=self.medicamento,
            concentracao="10 mg/mL",
            descricao="Frasco 500 mg",
            quantidade_mg=500,
        )
        self.item = ItemTransferencia.objects.create(
            transferencia=self.transferencia,
            apresentacao=self.apresentacao,
            quantidade=2,
        )

    def test_processa_evidencia_sem_dados_fica_requer_revisao(self):
        evidencia, extracao = processar_evidencia(
            self.transferencia, _imagem(), usuario=self.user, item=self.item
        )
        self.assertEqual(evidencia.item, self.item)
        self.assertTrue(evidencia.hash_arquivo)
        self.assertFalse(evidencia.suspeita_duplicidade)
        self.assertEqual(
            evidencia.status,
            TransferenciaEvidencia.StatusProcessamento.REQUER_REVISAO,
        )
        self.assertTrue(extracao.requer_revisao)

    def test_dados_completos_marcam_extraida(self):
        evidencia, extracao = processar_evidencia(
            self.transferencia,
            _imagem(),
            usuario=self.user,
            item=self.item,
            dados={
                "nome_produto": "Rituximabe 500 mg",
                "lote": "RIT-2026-01",
                "validade": date(2028, 5, 1),
            },
        )
        self.assertEqual(evidencia.status, TransferenciaEvidencia.StatusProcessamento.EXTRAIDA)
        self.assertFalse(extracao.requer_revisao)
        self.assertEqual(extracao.lote, "RIT-2026-01")

    def test_hash_duplicado_levanta_suspeita(self):
        processar_evidencia(self.transferencia, _imagem(), usuario=self.user)
        evidencia, _ = processar_evidencia(self.transferencia, _imagem(), usuario=self.user)
        self.assertTrue(evidencia.suspeita_duplicidade)

    def test_tamanho_acima_do_limite_rejeitado(self):
        grande = SimpleUploadedFile(
            "grande.png", b"x" * (11 * 1024 * 1024), content_type="image/png"
        )
        with self.assertRaises(ValueError):
            processar_evidencia(self.transferencia, grande, usuario=self.user)

    def test_extensao_proibida_rejeitada(self):
        executavel = SimpleUploadedFile("evil.exe", b"MZ", content_type="application/x-msdownload")
        with self.assertRaises(ValueError):
            processar_evidencia(self.transferencia, executavel, usuario=self.user)

    def test_arquivo_vazio_rejeitado(self):
        vazio = SimpleUploadedFile("vazio.png", b"", content_type="image/png")
        with self.assertRaises(ValueError):
            processar_evidencia(self.transferencia, vazio, usuario=self.user)

    def test_versoes_de_extracao_ficam_auditaveis(self):
        processar_evidencia(self.transferencia, _imagem(), usuario=self.user)
        processar_evidencia(
            self.transferencia,
            _imagem(),
            usuario=self.user,
            dados={"lote": "L1", "nome_produto": "X", "validade": date(2027, 1, 1)},
        )
        self.assertEqual(ExtracaoEvidencia.objects.count(), 2)
        evidencias = list(TransferenciaEvidencia.objects.filter(transferencia=self.transferencia))
        self.assertTrue(all(e.extracoes.count() == 1 for e in evidencias))
        self.assertTrue(evidencias[1].suspeita_duplicidade)

    def test_extracoes_sao_ordenadas_mais_recente_primeiro(self):
        processar_evidencia(
            self.transferencia, _imagem(nome="a.png"), usuario=self.user,
            dados={"lote": "L1", "nome_produto": "X", "validade": date(2027, 1, 1)},
        )
        processar_evidencia(
            self.transferencia, _imagem(nome="b.png"), usuario=self.user,
            dados={"lote": "L2", "nome_produto": "Y", "validade": date(2027, 2, 1)},
        )
        evidencia = TransferenciaEvidencia.objects.latest("criado_em")
        extracoes = list(evidencia.extracoes.all())
        self.assertEqual(extracoes[0].lote, "L2")

    def test_registrar_extracao_por_api_direta(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        arquivo = SimpleUploadedFile("f.png", b"\x89PNG", content_type="image/png")
        evidencia = TransferenciaEvidencia.objects.create(
            transferencia=self.transferencia,
            arquivo=arquivo,
            hash_arquivo="h" * 64,
        )
        extracao = registrar_extracao(
            evidencia, b"\x89PNG", dados={"lote": "DIR-1"}, usuario=self.user
        )
        self.assertEqual(extracao.engine, "mock")
        self.assertTrue(ExtracaoEvidencia.objects.filter(pk=extracao.pk).exists())