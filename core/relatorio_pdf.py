"""Parser do relatório de transferência (Ji-Paraná → Cacoal) em PDF.

Formato real "Transferência entre Estoques" (InterProcess/Unimed JPR):

    UNIMEDJPR 02/07/2026 10:46
    Transferência entre Estoques Página 1 de 1
    Origem: UNIMED CENTRO RONDÔNIA - Estoque: Estoque Ji-Parana
    Destino: Cacoal - Estoque: Estoque Principal Cacoal
    Descrição Lote Qtde Vl. Médio
    Tipo de Insumo: Medicamento
    24,0000 25,6440DIFENIDRIN 50 MG/ML  DIFENIDRIN ... X 1 M50034585
    10,0000 16,7457FAULDFLUOR 50 MG/ML ... X
    10 ML
    24l0388

Padrões observados:
- cada item começa com `QTD,0000 VALOR,MEDIO` (sem espaço entre valor e descrição);
- a descrição aparece duplicada (nome curto + descrição completa);
- o LOTE é o último token da linha (pode quebrar para a linha seguinte);
- seções separadas por "Tipo de Insumo: ...";
- o relatório NÃO contém validade — cabe à conferência obtê-la.

Fase 3 do módulo: extração textual com pypdf, hash SHA-256 para deduplicação
e resolução de aliases contra o cadastro local (SKILLS 03/04/05).
"""

import hashlib
import re
from datetime import datetime

from .services import normalizar_texto

# Início de item: "24,0000 25,6440" (qtde inteira + valor com vírgula).
_PADRAO_INICIO_ITEM = re.compile(r"^\s*(\d+),\d{4}\s+\d+,\d{4}")
# Lote: token único alfanumérico sem espaços (3–12 caracteres).
_PADRAO_LOTE = re.compile(r"^[A-Za-z0-9]{3,12}$")
# Cabeçalho: data no formato "UNIMEDJPR 02/07/2026 10:46".
_PADRAO_DATA_RELATORIO = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
# Linhas de moldura (origem/destino/página/rodapé).
_PADRAO_MOLDE = re.compile(
    r"^(origem:|destino:|transfer[^\w]|p[áa]gina|by interprocess|descri[çc][ãa]o lote)",
    re.IGNORECASE,
)
_PADRAO_TIPO_INSUMO = re.compile(r"^tipo de insumo:\s*(.+)$", re.IGNORECASE)

_ERROS = (ValueError, IndexError, KeyError, TypeError, AttributeError)


def calcular_hash(conteudo: bytes) -> str:
    """SHA-256 do arquivo original — chave de deduplicação de relatórios."""
    return hashlib.sha256(conteudo).hexdigest()


def _extrair_texto(conteudo: bytes) -> str:
    from io import BytesIO

    try:
        from pypdf import PdfReader

        leitor = PdfReader(BytesIO(conteudo))
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
    grupo = _PADRAO_DATA_RELATORIO.search(texto)
    if grupo:
        try:
            dia, mes, ano = grupo.group(1).split("/")
            return datetime(int(ano), int(mes), int(dia)).date()
        except ValueError:
            return None
    return None


def _parsear_destino(texto):
    for linha in texto.splitlines():
        if linha.strip().lower().startswith("destino:"):
            return linha.strip()
    return ""


def _remover_duplicacao(texto):
    """Remove prefixo repetido do relatório (nome curto duplicado na linha)."""
    partes = texto.split()
    for corte in range(len(partes) // 2, 0, -1):
        if partes[:corte] == partes[corte:2 * corte] and corte >= 2:
            return " ".join(partes[:corte]), " ".join(partes[corte:])
    return texto, ""


def _limpar_descricao(descricao):
    """Colapsa espaços e remove a repetição "nome nome-descrição-completa"."""
    descricao = " ".join(descricao.split())
    _, sem_duplicacao = _remover_duplicacao(descricao)
    return sem_duplicacao or descricao


def _separar_nome_e_descricao(descricao):
    """Separa o nome curto (segmento duplicado/primeiro bloco) da descrição."""
    nome, resto = _remover_duplicacao(descricao)
    if nome and resto:
        return nome, resto
    partes = descricao.split("  ")
    if len(partes) > 1:
        nome = partes[0].strip()
        resto = " ".join(p.strip() for p in partes[1:] if p.strip())
        if resto:
            return nome, resto
    return descricao, ""


def _linhas_para_itens(texto):
    """Quebra o texto bruto em blocos: (item, tipo_insumo_atual)."""
    blocos = []
    atual = {"linhas": [], "tipo": ""}
    for linha in texto.splitlines():
        l = linha.strip()
        if not l:
            continue
        tipo = _PADRAO_TIPO_INSUMO.search(l)
        if tipo:
            if atual["linhas"]:
                blocos.append(atual)
                atual = {"linhas": [], "tipo": ""}
            atual["tipo"] = tipo.group(1).strip()
            continue
        if _PADRAO_INICIO_ITEM.match(l):
            if atual["linhas"]:
                blocos.append(atual)
            atual = {"linhas": [l], "tipo": atual["tipo"]}
            continue
        if _PADRAO_MOLDE.match(l):
            continue
        if atual["linhas"]:
            atual["linhas"].append(l)
    if atual["linhas"]:
        blocos.append(atual)
    return blocos


def _extrair_lote_das_linhas(linhas):
    """Lote = último token alfanumérico compacto (pode estar na linha seguinte)."""
    texto = " ".join(linhas)
    tokens = texto.split()
    for indice in range(len(tokens) - 1, -1, -1):
        if _PADRAO_LOTE.match(tokens[indice]):
            return tokens[indice], indice
    return "", -1


def _montar_itens(blocos):
    itens = []
    for bloco in blocos:
        inicio = _PADRAO_INICIO_ITEM.match(bloco["linhas"][0])
        quantidade = int(inicio.group(1))
        primeira = _PADRAO_INICIO_ITEM.sub("", bloco["linhas"][0])
        tokens = " ".join([primeira] + bloco["linhas"][1:]).split()
        lote = ""
        for indice in range(len(tokens) - 1, -1, -1):
            if _PADRAO_LOTE.match(tokens[indice]):
                lote = tokens.pop(indice)
                break
        descricao = " ".join(tokens)
        nome, descricao_completa = _separar_nome_e_descricao(descricao)
        itens.append(
            {
                "quantidade": quantidade,
                "descricao": _limpar_descricao(descricao_completa) or nome,
                "nome": nome,
                "lote": lote,
                "tipo_insumo": bloco["tipo"],
            }
        )
    return itens


def extrair_relatorio(conteudo: bytes) -> dict:
    """Extrai dados do relatório: cabeçalho + itens (nome, descrição, lote, quantidade).

    Retorna:
        {
            "hash": str,
            "referencia_externa": str,
            "data_emissao": date | None,
            "itens": [{"nome", "descricao", "lote", "quantidade", "tipo_insumo"}, ...],
            "informativo": list[str],
        }
    """
    if not conteudo:
        raise ValueError("Relatório vazio.")
    texto = _extrair_texto(conteudo)
    if not texto.strip():
        raise ValueError("Não foi possível extrair texto do PDF.")

    blocos = _linhas_para_itens(texto)
    itens = _montar_itens(blocos)
    informativo = []
    for item in itens:
        if not item.get("lote"):
            informativo.append(
                f"Item sem lote identificado: {(item.get('nome') or item.get('descricao'))[:60]}"
            )
    if not itens:
        raise ValueError("Nenhum item de transferência reconhecido no relatório.")

    return {
        "hash": calcular_hash(conteudo),
        "referencia_externa": _parsear_destino(texto),
        "data_emissao": _parsear_data(texto),
        "itens": itens,
        "informativo": informativo,
    }


def resolver_descricao(clinica, descricao):
    """Resolve a descrição do relatório para apresentação cadastrada.

    Usa aliases aprovados (AliasMedicamento) e, em segundo lugar, a busca
    por nome do medicamento. Nunca cria registros.
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
        nome = normalizar_texto(medicamento.nome)
        if chave and nome and (nome.startswith(chave) or chave.startswith(nome)):
            apresentacoes = list(medicamento.apresentacoes.filter(ativa=True))
            if apresentacoes:
                return apresentacoes[0], medicamento, False
    return None, None, False


def reconhecer_itens(clinica, itens):
    """Interface pública: itens extraídos → (itens reconhecidos, não reconhecidos)."""
    reconhecidos = []
    nao_reconhecidos = []
    for item in itens:
        candidato = item.get("nome") or item.get("descricao")
        apresentacao, medicamento, via_alias = resolver_descricao(clinica, candidato)
        if apresentacao is None:
            nao_reconhecidos.append(
                {"descricao": candidato, "motivo": "medicamento não cadastrado"}
            )
            continue
        reconhecidos.append(
            {
                "apresentacao": apresentacao,
                "quantidade": item["quantidade"],
                "lote": item.get("lote", ""),
                "validade": item.get("validade"),
                "tipo_insumo": item.get("tipo_insumo", ""),
                "via_alias": via_alias,
                "descricao_original": candidato,
            }
        )
    return reconhecidos, nao_reconhecidos