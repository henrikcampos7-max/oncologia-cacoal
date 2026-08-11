"""Máquina de estados da conferência automatizada de transferências.

O fluxo completo do módulo (Ji-Paraná → Cacoal) é controlado por
``Transferencia.status_conferencia``; este módulo concentra as transições
válidas e as regras de guarda, mantendo as views enxutas (PROMPT_MESTRE
Fase 2 — Domínio).
"""

from .models import Transferencia

# Transições válidas: origem -> conjunto de destinos permitidos.
_TRANSICOES = {
    Transferencia.StatusConferencia.RASCUNHO: {
        Transferencia.StatusConferencia.RELATORIO_IMPORTADO,
        Transferencia.StatusConferencia.CANCELADA,
    },
    Transferencia.StatusConferencia.RELATORIO_IMPORTADO: {
        Transferencia.StatusConferencia.EM_TRANSITO,
        Transferencia.StatusConferencia.EM_CONFERENCIA,
        Transferencia.StatusConferencia.PENDENCIA_MANUAL,
        Transferencia.StatusConferencia.CANCELADA,
    },
    Transferencia.StatusConferencia.EM_TRANSITO: {
        Transferencia.StatusConferencia.AGUARDANDO_RECEBIMENTO,
        Transferencia.StatusConferencia.EM_CONFERENCIA,
        Transferencia.StatusConferencia.PENDENCIA_MANUAL,
        Transferencia.StatusConferencia.CANCELADA,
    },
    Transferencia.StatusConferencia.AGUARDANDO_RECEBIMENTO: {
        Transferencia.StatusConferencia.EM_CONFERENCIA,
        Transferencia.StatusConferencia.PENDENCIA_MANUAL,
        Transferencia.StatusConferencia.CANCELADA,
    },
    Transferencia.StatusConferencia.EM_CONFERENCIA: {
        Transferencia.StatusConferencia.PENDENCIA_MANUAL,
        Transferencia.StatusConferencia.DIVERGENCIA,
        Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO,
        Transferencia.StatusConferencia.CANCELADA,
    },
    Transferencia.StatusConferencia.PENDENCIA_MANUAL: {
        Transferencia.StatusConferencia.EM_CONFERENCIA,
        Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO,
        Transferencia.StatusConferencia.DIVERGENCIA,
        Transferencia.StatusConferencia.CANCELADA,
    },
    Transferencia.StatusConferencia.DIVERGENCIA: {
        Transferencia.StatusConferencia.EM_CONFERENCIA,
        Transferencia.StatusConferencia.PENDENCIA_MANUAL,
        Transferencia.StatusConferencia.CANCELADA,
    },
    Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO: {
        Transferencia.StatusConferencia.APROVADA,
        Transferencia.StatusConferencia.EM_CONFERENCIA,
        Transferencia.StatusConferencia.PENDENCIA_MANUAL,
        Transferencia.StatusConferencia.CANCELADA,
    },
    Transferencia.StatusConferencia.APROVADA: {
        Transferencia.StatusConferencia.INTEGRADA_AO_ESTOQUE,
        Transferencia.StatusConferencia.EM_CONFERENCIA,
        Transferencia.StatusConferencia.CANCELADA,
    },
    Transferencia.StatusConferencia.INTEGRADA_AO_ESTOQUE: set(),
    Transferencia.StatusConferencia.CANCELADA: set(),
}

# Estados terminais do fluxo de conferência.
ESTADOS_TERMINAIS = {
    Transferencia.StatusConferencia.INTEGRADA_AO_ESTOQUE,
    Transferencia.StatusConferencia.CANCELADA,
}

# Estados que representam fluxo bloqueado (requerem ação humana).
ESTADOS_BLOQUEADOS = {
    Transferencia.StatusConferencia.PENDENCIA_MANUAL,
    Transferencia.StatusConferencia.DIVERGENCIA,
}


class TransicaoInvalida(ValueError):
    """Transição de estado não prevista na máquina de conferência."""


def transicoes_possiveis(estado):
    """Conjunto de próximos estados permitidos a partir de ``estado``."""
    return frozenset(_TRANSICOES.get(estado, set()))


def pode_transicionar(origem, destino):
    if origem == destino:
        return False
    if origem not in _TRANSICOES:
        return False
    return destino in _TRANSICOES[origem]


def transicionar(transferencia, destino, usuario=None, motivo=""):
    """Aplica a transição validada e registra auditoria quando aplicável."""
    from .models import RegistroAuditoria
    from .services import registrar_auditoria

    origem = transferencia.status_conferencia
    if not pode_transicionar(origem, destino):
        raise TransicaoInvalida(
            f"Transição inválida: {origem} → {destino}. "
            f"Possíveis: {sorted(transicoes_possiveis(origem))}."
        )
    transferencia.status_conferencia = destino
    transferencia.save(update_fields=["status_conferencia", "atualizado_em"])
    if usuario is not None and transferencia.clinica_destino_id:
        registrar_auditoria(
            clinica=transferencia.clinica_destino,
            usuario=usuario,
            acao=f"Conferência de transferência {transferencia.numero}: {origem} → {destino}.",
            detalhes=motivo,
        )
    return transferencia


def sincronizar_status_operacional(transferencia):
    """Mantém o campo legado ``status`` coerente com o fluxo de conferência.

    A conferência passa a ser a fonte da verdade do recebimento; o status
    operacional reflete os estados de trânsito/recebimento para a tela antiga.
    """
    mapeamento = {
        Transferencia.StatusConferencia.RASCUNHO: Transferencia.Status.RASCUNHO,
        Transferencia.StatusConferencia.RELATORIO_IMPORTADO: Transferencia.Status.RASCUNHO,
        Transferencia.StatusConferencia.EM_TRANSITO: Transferencia.Status.EM_TRANSITO,
        Transferencia.StatusConferencia.AGUARDANDO_RECEBIMENTO: Transferencia.Status.EM_TRANSITO,
        Transferencia.StatusConferencia.EM_CONFERENCIA: Transferencia.Status.RECEBIDA,
        Transferencia.StatusConferencia.PENDENCIA_MANUAL: Transferencia.Status.RECEBIDA,
        Transferencia.StatusConferencia.DIVERGENCIA: Transferencia.Status.RECEBIDA,
        Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO: Transferencia.Status.RECEBIDA,
        Transferencia.StatusConferencia.APROVADA: Transferencia.Status.RECEBIDA,
        Transferencia.StatusConferencia.INTEGRADA_AO_ESTOQUE: Transferencia.Status.RECEBIDA,
        Transferencia.StatusConferencia.CANCELADA: Transferencia.Status.CANCELADA,
    }
    operacional = mapeamento.get(transferencia.status_conferencia)
    if operacional is not None and transferencia.status != operacional:
        transferencia.status = operacional
        transferencia.save(update_fields=["status", "atualizado_em"])
    return transferencia