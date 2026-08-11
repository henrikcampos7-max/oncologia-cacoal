"""Parser do relatório de transferência (Ji-Paraná → Cacoal) em PDF.

Fase 3 do módulo: extração textual com pypdf, hash SHA-256 para deduplicação,
normalização de nomes e resolução de aliases contra o cadastro local
(SKILLS 03/04/05). Não altera dados: apenas lê o PDF e devolve estrutura.
"""

import hashlib
import re
from datetime import datetime

from .services import normalizar_texto

# Padrões de linha do relatório "rev. 77": item | descrição | ... | validade | lote | quantidade.
_PADRAO_ITEM = re.compile(
    r"^\s*(\d{1,4})[.)]\s+(?P<descricao>.+?)\s+"
    r"(?P<validade>\d{2}/\d{2}/\d{4}|\d{2}/\d{4})\s+"
    r"(?P<lote>[A-Za-z0-9\-_./]{2,30})\s+"
    r"(?P<quantidade>\d{1,6})\s*$"
)
_PADRAO_ITEM_SEM_LOTE = re.compile(
    r"^\s*(\d{1,4})[.)]\s+(?P<descricao>.+?)\s+"
    r"(?P<validade>\d{2}/\d{2}/\d{4}|\d{2}/\d{4})\s+"
    r"(?P<quantidade>\d{1,6})\s*$"
)
_PADRAO_DATA_RELATORIO = re.compile(r"(\d{2}/\d{2}/\d{4})")
_PADRAO_REFERENCIA = re.compile(
    r"(?:ct[\.:]?\s*|guia\s*[:#]\s*|ref[\.:]?\s*)([A-Z]{0,6}\s?\d{3,10}[A-Z]{0,3})",
    re.IGNORECASE,
)
_CAMPOS_OPCIONAIS = (r"atividade", r"prof\.", r"farmac\w*", r"rev\.?\s*\d+")

_ERROS = (ValueError, IndexError, KeyError, TypeError, AttributeError)


def calcular_hash(conteudo: bytes) -> str:
    """SHA-256 do arquivo original — chave de deduplicação de relatórios."""
    return hashlib.sha256(conteudo).hexdigest()


def _extrair_texto(conteudo: bytes) -> str:
    try:
        from pypdf import PdfReader

        leitor = PdfReader(conteudo)
        paginas = []
        for pagina in leitor.pages:
            try:
                paginas.append(pagina.extract_text() or "")
            except _ERROS:
                continue
        return "\n".join(paginas)
    except ImportError:
        raise RuntimeError(
            "pypdf não instalado — execute: pip install pypdf"
        ) from None


def _parsear_data(texto):
    for padrao in (_PADRAO_DATA_RELATORIO,):
        for grupo in padrao.findall(texto):
            try:
                valores = grupo.split("/")
                if len(valores) == 3:
                    return datetime(int(valores[2]), int(valores[1]), int(valores[0])).date()
            except ValueError:
                continue
    return None


def _parsear_referencia(texto):
    for linha in texto.splitlines():
        grupo = _PADRAO_REFERENCIA.search(linha)
        if grupo:
            return grupo.group(1).strip()
    return ""


def extrair_relatorio(conteudo: bytes) -> dict:
    """Extrai dados do relatório: cabeçalho + itens (descrição, lote, validade, quantidade).

    Retorna:
        {
            "hash": str,
            "referencia_externa": str,
            "data_emissao": date | None,
            "itens": [{"descricao", "validade", "lote", "quantidade"}, ...],
            "informativo": list[str],   # avisos de normalização (ex.: sem lote)
        }
    """
    if not conteudo:
        raise ValueError("Relatório vazio.")
    texto = _extrair_texto(conteudo)
    if not texto.strip():
        raise ValueError("Não foi possível extrair texto do PDF.")

    itens = []
    informativo = []
    for linha in texto.splitlines():
        for padrao in (_PADRAO_ITEM, _PADRAO_ITEM_SEM_LOTE):
            grupo = padrao.match(linha.strip())
            if not grupo:
                continue
            dados = grupo.groupdict()
            lote = (dados.get("lote") or "").strip()
            if not lote:
                informativo.append(
                    f"Item sem lote identificado: {dados['descricao'][:60]}"
                )
            try:
                validade = datetime.strptime(dados["validade"], "%d/%m/%Y").date()
            except ValueError:
                try:
                    validade = datetime.strptime(dados["validade"], "%m/%Y").date()
                except ValueError:
                    validade = None
                    informativo.append(
                        f"Validade com formato não reconhecido: {dados['validade']}"
                    )
            itens.append(
                {
                    "descricao": (dados["descricao"] or "").strip(),
                    "validade": validade,
                    "lote": lote,
                    "quantidade": int(dados["quantidade"]),
                }
            )
            break
        else:
            if _encontra_cabecalho_opcional(linha):
                continue
            informativo.append(f"Linha não reconhecida: {linha.strip()[:80]}")
    if not itens:
        raise ValueError("Nenhum item de transferência reconhecido no relatório.")

    return {
        "hash": calcular_hash(conteudo),
        "referencia_externa": _parsear_referencia(texto),
        "data_emissao": _parsear_data(texto),
        "itens": itens,
        "informativo": informativo,
    }


def _encontra_cabecalho_opcional(linha):
    """Linhas de cabeçalho/rodapé (atividade, assinatura, revisão) não são divergências."""
    l = normalizar_texto(linha)
    if not l:
        return True
    return any(re.search(p, l) for p in _CAMPOS_OPCIONAIS)


def resolver_descricao(clinica, descricao):
    """Resolve a descrição do relatório para apresentação cadastrada.

    Usa aliases aprovados (AliasMedicamento) e, em segundo lugar, a busca
    fuzzy por nome do medicamento. Nunca cria registros.
    """
    from .models import AliasMedicamento, Medicamento

    chave = normalizar_texto(descricao)
    aliases = AliasMedicamento.objects.filter(clinica=clinica)
    for alias in aliases.select_related("medicamento"):
        if normalizar_texto(alias.alias) == chave:
            apresentacoes = list(alias.medicamento.apresentacoes.filter(ativa=True))
            if apresentacoes:
                return apresentacoes[0], alias.medicamento, True

    for medicamento in Medicamento.objects.filter(clinica=clinica):
        primeira_palavra = chave.split(" ")[0] if chave else ""
        nome = normalizar_texto(medicamento.nome)
        if primeira_palavra and nome.startswith(primeira_palavra):
            apresentacoes = list(medicamento.apresentacoes.filter(ativa=True))
            if apresentacoes:
                return apresentacoes[0], medicamento, False
    return None, None, False


def _itera_itens_relatorio(clinica, itens):
    """Reconhece cada item do relatório em apresentação local ou alias.

    Retorno: (lista_ok, lista_nao_reconhecidos, detalhes)
    """
    reconhecidos = []
    nao_reconhecidos = []
    for item in itens:
        apresentacao, medicamento, via_alias = resolver_descricao(clinica, item["descricao"])
        if apresentacao is None:
            nao_reconhecidos.append(
                {"descricao": item["descricao"], "motivo": "medicamento não cadastrado"}
            )
            continue
        reconhecidos.append(
            {
                "apresentacao": apresentacao,
                "quantidade": item["quantidade"],
                "lote": item["lote"],
                "validade": item["validade"],
                "via_alias": via_alias,
                "descricao_original": item["descricao"],
            }
        )
    return reconhecidos, nao_reconhecidos


def reconhecer_itens(clinica, itens):
    """Interface pública: itens extraídos → (itens reconhecidos, não reconhecidos)."""
    return _itera_itens_relatorio(clinica, itens)