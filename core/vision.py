"""Abstração de visão computacional para a conferência de transferências.

SKILLS 06–16: cada evidência fotográfica passa por um *provider* que extrai
campos estruturados (produto, lote, validade, quantidade). O provider ativo
é escolhido por ambiente (``TRANSFER_VISION_PROVIDER``):

- ``manual``: dados digitados pelo usuário no formulário (dicionário).
- ``mock``: determinístico, sem OCR — campos ausentes ficam vazios, o que
  força revisão humana (nunca inventamos lote/validade).

Providers externos (OCR real) plugam implementando ``ProviderBase`` sem
alterar views.
"""

import hashlib

from django.conf import settings

CAMPOS_EXTRAIDOS = (
    "nome_produto",
    "principio_ativo",
    "apresentacao",
    "lote",
    "validade",
    "fabricacao",
    "quantidade",
    "codigo_gs1",
    "lote_gs1",
    "validade_gs1",
    "confianca_produto",
    "confianca_lote",
    "confianca_validade",
    "confianca_quantidade",
    "requer_revisao",
)


class ProviderBase:
    """Contrato mínimo de um provider de visão. Implementações devem ser
    determinísticas para dados idênticos (auditoria)."""

    engine = "base"

    def extract_image(self, arquivo_bytes, dados=None):
        raise NotImplementedError

    def classify_qa(self, texto):
        raise NotImplementedError


class ManualProvider(ProviderBase):
    """Extração a partir de dados digitados manualmente (''extract'' humano)."""

    engine = "manual"

    def extract_image(self, arquivo_bytes, dados=None):
        dados = dados or {}
        quant = dados.get("quantidade")
        try:
            quant = int(quant) if quant not in (None, "") else None
        except (TypeError, ValueError):
            quant = None
        campos = {
            "nome_produto": (dados.get("nome_produto") or "").strip(),
            "principio_ativo": (dados.get("principio_ativo") or "").strip(),
            "apresentacao": (dados.get("apresentacao") or "").strip(),
            "lote": (dados.get("lote") or "").strip(),
            "validade": dados.get("validade"),
            "fabricacao": dados.get("fabricacao"),
            "quantidade": quant,
            "codigo_gs1": (dados.get("codigo_gs1") or "").strip(),
            "lote_gs1": (dados.get("lote_gs1") or "").strip(),
            "validade_gs1": dados.get("validade_gs1"),
            "confianca_produto": dados.get("confianca_produto", 1),
            "confianca_lote": dados.get("confianca_lote", 1),
            "confianca_validade": dados.get("confianca_validade", 1),
            "confianca_quantidade": dados.get("confianca_quantidade", 1),
            "requer_revisao": bool(dados.get("requer_revisao", False)),
        }
        return campos

    def classify_qa(self, texto):
        texto = (texto or "").strip().upper()
        if "NAO APROVADO" in texto or "NAO APROVADA" in texto:
            return "nao_aprovado", 1.0
        if texto in ("APROVADO", "APROVADA"):
            return "aprovado", 1.0
        return None, 0.0


class MockProvider(ProviderBase):
    """Provider determinístico sem OCR: nunca inventa lote/validade.

    Campos ausentes permanecem vazios e marcam ``requer_revisao=True``,
    garantindo que falso-positivos não entrem no estoque (SKILL 21/22).
    Dados opcionais fornecidos via ``dados`` são aceitos (modo "mock" com
    entrada assistida) e replicam o comportamento do ManualProvider.
    """

    engine = "mock"

    def __init__(self):
        self._deterministico = True

    def extract_image(self, arquivo_bytes, dados=None):
        dados = dados or {}
        quant = dados.get("quantidade")
        try:
            quant = int(quant) if quant not in (None, "") else None
        except (TypeError, ValueError):
            quant = None
        lote = (dados.get("lote") or "").strip()
        validade = dados.get("validade")
        confiancas = {
            "confianca_produto": 1 if dados.get("nome_produto") else 0,
            "confianca_lote": 1 if lote else 0,
            "confianca_validade": 1 if validade else 0,
            "confianca_quantidade": 1 if quant else 0,
        }
        requer = not (dados.get("nome_produto") and lote and validade)
        return {
            "nome_produto": (dados.get("nome_produto") or "").strip(),
            "principio_ativo": (dados.get("principio_ativo") or "").strip(),
            "apresentacao": (dados.get("apresentacao") or "").strip(),
            "lote": lote,
            "validade": validade,
            "fabricacao": dados.get("fabricacao"),
            "quantidade": quant,
            "codigo_gs1": (dados.get("codigo_gs1") or "").strip(),
            "lote_gs1": (dados.get("lote_gs1") or "").strip(),
            "validade_gs1": dados.get("validade_gs1"),
            **confiancas,
            "requer_revisao": requer,
        }

    def classify_qa(self, texto):
        # Classificação determinística para "liberado"/"não liberado".
        texto = (texto or "").strip().upper()
        if "NAO" in texto:
            return "nao_aprovado", 1.0
        if texto in ("APROVADO", "APROVADA", "OK", "LIBERADO"):
            return "aprovado", 1.0
        return None, 0.0


class _OcrHttpProxy:
    """Interface de HTTP minimamente mockável para os providers externos.

    Os providers usam exclusivamente a biblioteca padrão (``urllib.request``).
    Em testes injetamos um proxy determinístico, evitando chamadas pagas.
    """

    def abrir(self, request):
        import urllib.request

        return urllib.request.urlopen(request, timeout=_timeout_oc())  # noqa: S310

    def ler_json(self, response):
        import json

        conteudo = response.read()
        return json.loads(conteudo.decode("utf-8"))


def _timeout_oc():
    return settings.TRANSFER_CONFERENCE_CONFIG.get("vision_timeout_segundos", 60)


def _padrao_label(campo):
    """Retorna regex para linha rotulada: ``LOTE: X``, ``Validade: X`` etc."""
    import re

    return re.compile(rf"^\s*{campo}\s*[:.\-]?\s*(.+?)\s*$", re.IGNORECASE)


def _extrair_validade(texto):
    """Procura datas de validade em formatos comuns brasileiros.

    Retorna (validade_iso, confianca). Nunca inventa: ausente → (None, 0.0).
    """
    import re

    padroes = [
        (r"\b(\d{2})[/.](\d{2})[/.](\d{4})\b", "%d/%m/%Y"),
        (r"\b(\d{4})-(\d{2})-\d{2}\b", "%d/%m/%Y"),
        (r"\b(\d{2})/(\d{4})\b", "%d/%m/%Y"),
    ]
    for regex, _ in padroes:
        match = re.search(regex, texto)
        if not match:
            continue
        grupos = match.groups()
        try:
            if len(grupos) == 3:
                dia, mes, ano = (int(g) for g in grupos)
            else:
                mes, ano = (int(g) for g in grupos)
                dia = 1
            from datetime import date

            if not (1 <= mes <= 12 and 1 <= dia <= 31 and 1900 <= ano <= 2100):
                continue
            validade = date(ano, mes, dia)
            if validade < date(2000, 1, 1):
                continue
            return validade.isoformat(), 1.0
        except ValueError:
            continue
    return None, 0.0


def _normalizar_lote(lote):
    import re

    lote = (lote or "").strip().upper()
    lote = re.sub(r"\s+", "", lote)
    if not re.fullmatch(r"[A-Z0-9-]{3,12}", lote):
        return ""
    return lote


def _parsear_ocr(texto):
    """Converte texto bruto do OCR em campos estruturados (conservador).

    Regras de segurança (SKILL 21/22):
    - só preenche lote com padrão validado (3–12 alfanuméricos);
    - validade somente com data plausível;
    - quantidade somente quando rotulada (QTD/QTDE/QDE);
    - nome do produto apenas quando rotulado; caso contrário fica vazio
      (exige revisão humana) — nunca inferimos por heurística.
    """
    import re

    lote = ""
    lote_conf = 0.0
    rotulado = _padrao_label("lote").search(texto) or re.search(
        r"\blote\b\s*[:.\-]?\s*([A-Z0-9\-/]{3,15})", texto, re.IGNORECASE
    )
    if rotulado:
        candidato = _normalizar_lote(rotulado.group(1))
        if candidato:
            lote, lote_conf = candidato, 1.0

    validade, validade_conf = _extrair_validade(texto)

    quantidade = None
    quantidade_conf = 0.0
    quantidade_rotulado = re.search(
        r"\b(?:qtd|qtde|qde|quantidade)\b\s*[:.\-]?\s*(\d+)",
        texto,
        re.IGNORECASE,
    )
    if quantidade_rotulado:
        try:
            quantidade = int(quantidade_rotulado.group(1))
            quantidade_conf = 1.0
        except ValueError:
            pass

    nome_produto = ""
    produto_conf = 0.0
    produto_rotulado = _padrao_label("PRODUTO").search(texto) or re.search(
        r"\bproduto\b\s*[:.\-]?\s*(.+)", texto, re.IGNORECASE
    )
    if produto_rotulado:
        nome = produto_rotulado.group(1).strip()
        if len(nome) >= 3:
            nome_produto, produto_conf = nome, 1.0

    return {
        "nome_produto": nome_produto,
        "principio_ativo": "",
        "apresentacao": "",
        "lote": lote,
        "validade": validade,
        "fabricacao": None,
        "quantidade": quantidade,
        "codigo_gs1": "",
        "lote_gs1": "",
        "validade_gs1": None,
        "confianca_produto": produto_conf,
        "confianca_lote": lote_conf,
        "confianca_validade": validade_conf,
        "confianca_quantidade": quantidade_conf,
        "requer_revisao": bool(not (nome_produto and lote and validade)),
    }


def _montar_campos_base(parsed):
    return {
        "nome_produto": parsed.get("nome_produto", ""),
        "principio_ativo": parsed.get("principio_ativo", ""),
        "apresentacao": parsed.get("apresentacao", ""),
        "lote": parsed.get("lote", ""),
        "validade": parsed.get("validade"),
        "fabricacao": parsed.get("fabricacao"),
        "quantidade": parsed.get("quantidade"),
        "codigo_gs1": parsed.get("codigo_gs1", ""),
        "lote_gs1": parsed.get("lote_gs1", ""),
        "validade_gs1": parsed.get("validade_gs1"),
        "confianca_produto": parsed.get("confianca_produto", 0),
        "confianca_lote": parsed.get("confianca_lote", 0),
        "confianca_validade": parsed.get("confianca_validade", 0),
        "confianca_quantidade": parsed.get("confianca_quantidade", 0),
        "requer_revisao": bool(parsed.get("requer_revisao", True)),
    }


class AzureDocumentIntelligenceProvider(ProviderBase):
    """OCR real via Azure AI Document Intelligence (prebuilt-layout).

    Configuração por variável de ambiente (nenhuma chave no repositório):
    - ``TRANSFER_AZURE_ENDPOINT``: URL do recurso (ex.: https://x.cognitiveservices.azure.com/);
    - ``TRANSFER_AZURE_KEY``: chave de autenticação;
    - ``TRANSFER_AZURE_API_VERSION``: versão da API (padrão 2024-11-30);
    - ``TRANSFER_AZURE_MODEL``: modelo (padrão prebuilt-layout).

    Falhas de configuração ou rede levantam ``RuntimeError`` com orientação;
    o pipeline registra a evidência como FALHOU e exige retentativa —
    nenhum campo é inventado em caso de erro.
    """

    engine = "azure_document_intelligence"

    def __init__(self, proxy=None):
        self._proxy = proxy or _OcrHttpProxy()

    def _config(self):
        cfg = settings.TRANSFER_CONFERENCE_CONFIG.get("azure", {})
        endpoint = (cfg.get("endpoint") or "").rstrip("/")
        chave = cfg.get("chave") or ""
        if not endpoint or not chave:
            raise RuntimeError(
                "Provider Azure não configurado. Defina TRANSFER_AZURE_ENDPOINT e "
                "TRANSFER_AZURE_KEY (variáveis de ambiente) ou troque o provider."
            )
        return cfg, endpoint, chave

    def extract_image(self, arquivo_bytes, dados=None):
        import json
        import time
        import urllib.error as urlerror
        import urllib.parse
        import urllib.request as urlreq

        cfg, endpoint, chave = self._config()
        api_version = cfg.get("api_version", "2024-11-30")
        modelo = cfg.get("modelo", "prebuilt-layout")

        url = (
            f"{endpoint}/documentintelligence/documentModels/{modelo}:analyze"
            f"?api-version={urllib.parse.quote(api_version)}"
        )
        pedido = urlreq.Request(
            url,
            data=arquivo_bytes,
            headers={
                "Content-Type": "image/jpeg",
                "Ocp-Apim-Subscription-Key": chave,
            },
            method="POST",
        )
        try:
            resposta = self._proxy.abrir(pedido)
            operation_location = resposta.headers.get("operation-location") or ""
            resposta.close()
        except urlerror.HTTPError as exc:
            raise RuntimeError(
                f"Azure retornou HTTP {exc.code} ({exc.reason}). "
                f"Verifique endpoint, chave e cota do recurso."
            ) from exc
        except urlerror.URLError as exc:
            raise RuntimeError(
                f"Falha de rede ao chamar Azure Document Intelligence: {exc.reason}"
            ) from exc
        if not operation_location:
            raise RuntimeError(
                "Azure não retornou localização de operação (operation-location)."
            )

        texto = ""
        for _ in range(20):
            time.sleep(1)
            consulta = urlreq.Request(
                operation_location,
                headers={"Ocp-Apim-Subscription-Key": chave},
                method="GET",
            )
            try:
                estado = self._proxy.ler_json(self._proxy.abrir(consulta))
            except urlerror.HTTPError as exc:
                raise RuntimeError(f"Azure falhou ao consultar resultado (HTTP {exc.code}).") from exc
            status = estado.get("status")
            if status == "succeeded":
                texto = estado.get("content") or estado.get("analyzeResult", {}).get("content", "")
                break
            if status == "failed":
                raise RuntimeError("Azure Document Intelligence falhou no processamento da imagem.")
        if not texto.strip():
            raise ValueError("Azure não extraiu texto da imagem.")
        return _montar_campos_base(_parsear_ocr(texto))

    def classify_qa(self, texto):
        raise NotImplementedError


class GoogleVisionProvider(ProviderBase):
    """OCR real via Google Cloud Vision (TEXT_DETECTION).

    Configuração por variável de ambiente:
    - ``TRANSFER_GOOGLE_TOKEN``: token OAuth 2.0 (obtido fora do app);
    - ``TRANSFER_GOOGLE_API_ENDPOINT``: endpoint padrão já configurado.

    Requer escopo Cloud Vision no token. Falhas de configuração ou rede
    levantam ``RuntimeError`` com orientação; nenhum campo é inventado.
    """

    engine = "google_cloud_vision"

    def __init__(self, proxy=None):
        self._proxy = proxy or _OcrHttpProxy()

    def _config(self):
        cfg = settings.TRANSFER_CONFERENCE_CONFIG.get("google", {})
        token = cfg.get("token") or ""
        endpoint = cfg.get("api_endpoint") or "https://vision.googleapis.com/v1/images:annotate"
        if not token:
            raise RuntimeError(
                "Provider Google não configurado. Defina TRANSFER_GOOGLE_TOKEN "
                "(token OAuth 2.0 com escopo Cloud Vision) ou troque o provider."
            )
        return token, endpoint

    def extract_image(self, arquivo_bytes, dados=None):
        import base64
        import json
        import urllib.error as urlerror
        import urllib.request as urlreq

        token, endpoint = self._config()
        payload = {
            "requests": [
                {
                    "image": {"content": base64.b64encode(arquivo_bytes).decode("ascii")},
                    "features": [{"type": "TEXT_DETECTION"}],
                }
            ]
        }
        pedido = urlreq.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        try:
            resposta = self._proxy.ler_json(self._proxy.abrir(pedido))
        except urlerror.HTTPError as exc:
            raise RuntimeError(
                f"Google Vision retornou HTTP {exc.code} ({exc.reason}). "
                f"Verifique o token e a cota do projeto."
            ) from exc
        except urlerror.URLError as exc:
            raise RuntimeError(
                f"Falha de rede ao chamar Google Cloud Vision: {exc.reason}"
            ) from exc
        erros = resposta.get("responses", [{}])[0].get("error")
        if erros:
            raise RuntimeError(
                f"Google Vision rejeitou a imagem: {erros.get('message', 'erro desconhecido')}"
            )
        anotacoes = resposta.get("responses", [{}])[0].get("textAnnotations") or []
        texto = anotacoes[0].get("description", "") if anotacoes else ""
        if not texto.strip():
            raise ValueError("Google Vision não extraiu texto da imagem.")
        return _montar_campos_base(_parsear_ocr(texto))

    def classify_qa(self, texto):
        raise NotImplementedError


class ProviderFactory:
    @staticmethod
    def obter_provider(nome=None):
        nome = nome or settings.TRANSFER_CONFERENCE_CONFIG.get("vision_provider", "mock")
        provedores = {
            "manual": ManualProvider,
            "mock": MockProvider,
            "azure": AzureDocumentIntelligenceProvider,
            "google": GoogleVisionProvider,
        }
        classe = provedores.get(nome)
        if classe is None:
            raise ValueError(
                f"Provider de visão desconhecido: {nome!r}. "
                f"Disponíveis: {sorted(provedores)}."
            )
        return classe()


def resumo_aprovacao(extracao):
    """Critério final de liberação: todos os campos obrigatórios confirmados.

    Retorna (aprovado: bool, motivo: str).
    """
    obrigatorios = {
        "produto": extracao.get("nome_produto"),
        "lote": extracao.get("lote"),
        "validade": extracao.get("validade"),
    }
    ausentes = [campo for campo, valor in obrigatorios.items() if not valor]
    if ausentes:
        return False, "Campos ausentes: " + ", ".join(ausentes)
    limiar = settings.TRANSFER_CONFERENCE_CONFIG["confianca"]["alta"]
    baixos = [
        campo
        for campo in ("confianca_produto", "confianca_lote", "confianca_validade")
        if (extracao.get(campo) or 0) < limiar
    ]
    if baixos:
        return False, "Confiança abaixo do limiar: " + ", ".join(baixos)
    return True, ""


def _validar_arquivo(arquivo):
    import os

    config = settings.TRANSFER_CONFERENCE_CONFIG
    limite = config["tamanho_maximo_evidencia_mb"] * 1024 * 1024
    if arquivo.size > limite:
        raise ValueError(
            f"Arquivo excede {config['tamanho_maximo_evidencia_mb']} MB."
        )
    extensao = os.path.splitext(arquivo.name)[1].lstrip(".").lower()
    if extensao not in config["imagens_permitidas"]:
        raise ValueError(
            f"Formato {extensao or 'desconhecido'} não permitido "
            f"(permitidos: {', '.join(config['imagens_permitidas'])})."
        )


def registrar_extracao(evidencia, arquivo_bytes, dados=None, usuario=None, provider=None):
    from decimal import Decimal

    from .models import ExtracaoEvidencia

    provider = provider or ProviderFactory.obter_provider()
    campos = provider.extract_image(arquivo_bytes, dados=dados)
    decimal_field = lambda v: Decimal(str(float(v))) if v not in (None, "") else None
    extracao = ExtracaoEvidencia.objects.create(
        evidencia=evidencia,
        nome_produto=campos.get("nome_produto", ""),
        principio_ativo=campos.get("principio_ativo", ""),
        apresentacao=campos.get("apresentacao", ""),
        lote=campos.get("lote", ""),
        validade=campos.get("validade"),
        fabricacao=campos.get("fabricacao"),
        quantidade=campos.get("quantidade"),
        codigo_gs1=campos.get("codigo_gs1", ""),
        lote_gs1=campos.get("lote_gs1", ""),
        validade_gs1=campos.get("validade_gs1"),
        confianca_produto=decimal_field(campos.get("confianca_produto")),
        confianca_lote=decimal_field(campos.get("confianca_lote")),
        confianca_validade=decimal_field(campos.get("confianca_validade")),
        confianca_quantidade=decimal_field(campos.get("confianca_quantidade")),
        engine=provider.engine,
        requer_revisao=bool(campos.get("requer_revisao", True)),
        extraido_por=usuario,
    )
    return extracao


def processar_evidencia(transferencia, arquivo, usuario=None, item=None, dados=None):
    """Pipeline completo de uma evidência: validação → hash → duplicidade →
    persistência → extração → status. Retorna (evidencia, extracao)."""
    from .models import TransferenciaEvidencia

    _validar_arquivo(arquivo)
    conteudo = arquivo.read()
    arquivo.seek(0)
    if not conteudo:
        raise ValueError("Arquivo vazio.")

    hash_arquivo = hashlib.sha256(conteudo).hexdigest()
    duplicada = TransferenciaEvidencia.objects.filter(
        hash_arquivo=hash_arquivo
    ).exists()

    evidencia = TransferenciaEvidencia.objects.create(
        transferencia=transferencia,
        item=item,
        arquivo=arquivo,
        hash_arquivo=hash_arquivo,
        suspeita_duplicidade=duplicada,
        status=TransferenciaEvidencia.StatusProcessamento.PROCESSANDO,
        enviado_por=usuario,
    )
    evidencia.arquivo.save(
        f"evidencia_{hash_arquivo[:12]}{__import__('os').path.splitext(arquivo.name)[1].lower()}",
        arquivo,
        save=True,
    )
    try:
        extracao = registrar_extracao(evidencia, conteudo, dados=dados, usuario=usuario)
    except Exception:
        evidencia.status = TransferenciaEvidencia.StatusProcessamento.FALHOU
        evidencia.save(update_fields=["status"])
        raise
    evidencia.status = (
        TransferenciaEvidencia.StatusProcessamento.REQUER_REVISAO
        if extracao.requer_revisao
        else TransferenciaEvidencia.StatusProcessamento.EXTRAIDA
    )
    evidencia.save(update_fields=["status"])
    return evidencia, extracao