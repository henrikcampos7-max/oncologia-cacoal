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


class ProviderFactory:
    @staticmethod
    def obter_provider(nome=None):
        nome = nome or settings.TRANSFER_CONFERENCE_CONFIG.get("vision_provider", "mock")
        provedores = {
            "manual": ManualProvider,
            "mock": MockProvider,
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