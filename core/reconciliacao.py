"""Reconciliação esperado × observado da conferência de transferências.

SKILLS 17–22: compara itens do relatório (esperado) com a extração das
evidências (observado), tipa divergências e computa o estado da conferência.
Nada é alterado aqui fora do registro de reconciliação/divergência — a
integração ao estoque acontece somente após aprovação (Fase 8).
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .conferencia import pode_transicionar, sincronizar_status_operacional, transicionar
from .models import (
    DivergenciaTransferencia,
    ReconciliacaoItemTransferencia,
    StatusReconciliacao,
    Transferencia,
)


def criar_reconciliacoes_para_transferencia(transferencia):
    """Garante uma reconciliação por item (nunca cria itens novos)."""
    itens = transferencia.itens.select_related("apresentacao__medicamento")
    criadas = 0
    for item in itens:
        _, criada = ReconciliacaoItemTransferencia.objects.get_or_create(item=item)
        if criada:
            criadas += 1
    return criadas


def classificar_validade(data_validade, hoje=None):
    """Classifica a validade observada: ok | critica | desconhecida | vencida."""
    if data_validade is None:
        return "desconhecida"
    hoje = hoje or timezone.localdate()
    if data_validade < hoje:
        return "vencida"
    if data_validade <= hoje + timedelta(
        days=settings.TRANSFER_CONFERENCE_CONFIG["validade_critica_dias"]
    ):
        return "critica"
    return "ok"


def registrar_divergencia(transferencia, tipo, valor_esperado, valor_observado,
                          severidade=None, item=None, resolucao=""):
    severidade = severidade or DivergenciaTransferencia.Severidade.MEDIA
    return DivergenciaTransferencia.objects.create(
        transferencia=transferencia,
        item=item,
        tipo=tipo,
        severidade=severidade,
        valor_esperado=valor_esperado or "",
        valor_observado=valor_observado or "",
        status=(
            DivergenciaTransferencia.StatusResolucao.RESOLVIDA
            if resolucao
            else DivergenciaTransferencia.StatusResolucao.PENDENTE
        ),
        resolucao=resolucao,
    )


def reconciliar_item(item, observado, usuario=None, anotacoes=""):
    """Compara a extração ``observado`` com o esperado do ``item``.

    ``observado`` (dict): produto_observado (Apresentacao|None), lote,
    validade, quantidade, foto_insuficiente (bool), confianca_final.
    Atualiza ReconciliacaoItemTransferencia, cria divergências tipadas e
    propaga o status final para o item. Devolve a reconciliação atualizada.
    """
    transferencia = item.transferencia
    reconciliacao, _ = ReconciliacaoItemTransferencia.objects.get_or_create(item=item)

    produto = observado.get("produto_observado")
    lote = (observado.get("lote") or "").strip()
    validade = observado.get("validade")
    quantidade = observado.get("quantidade")
    foto_insuficiente = bool(observado.get("foto_insuficiente"))

    reconciliacao.produto_observado = produto
    reconciliacao.lote_observado = lote
    reconciliacao.validade_observada = validade
    reconciliacao.quantidade_observada = quantidade
    reconciliacao.confianca_final = observado.get("confianca_final")
    reconciliacao.anotacoes = anotacoes
    reconciliacao.revisado_por = usuario
    reconciliacao.revisado_em = timezone.now()

    def salvar(status):
        reconciliacao.status_final = status
        reconciliacao.save()

    if foto_insuficiente:
        reconciliacao.match_produto = produto is not None
        reconciliacao.match_lote = None
        reconciliacao.match_quantidade = None
        reconciliacao.status_validade = "desconhecida"
        salvar(StatusReconciliacao.FOTO_INSUFICIENTE)
        registrar_divergencia(
            transferencia,
            DivergenciaTransferencia.Tipo.FOTO_INSUFICIENTE,
            f"{item.apresentacao} (qtd {item.quantidade})",
            "foto sem leitura suficiente",
            severidade=DivergenciaTransferencia.Severidade.MEDIA,
            item=item,
        )
        return reconciliacao

    produto_ok = produto is not None and produto.pk == item.apresentacao.pk
    reconciliacao.match_produto = produto_ok
    if not produto_ok:
        reconciliacao.status_validade = classificar_validade(validade)
        salvar(
            StatusReconciliacao.DIVERGENCIA_PRODUTO
            if produto is not None
            else StatusReconciliacao.DIVERGENCIA_APRESENTACAO
        )
        registrar_divergencia(
            transferencia,
            DivergenciaTransferencia.Tipo.PRODUTO
            if produto is not None
            else DivergenciaTransferencia.Tipo.APRESENTACAO,
            f"{item.apresentacao} (qtd {item.quantidade})",
            str(produto) if produto else "não identificado",
            severidade=DivergenciaTransferencia.Severidade.CRITICA,
            item=item,
        )
        return reconciliacao

    class_validade = classificar_validade(validade)
    reconciliacao.status_validade = class_validade
    # Sem lote esperado persistido no item (o relatório não guarda lote por item),
    # o lote informado na evidência é aceito; ausência fica "não verificado".
    reconciliacao.match_lote = True if lote else None
    reconciliacao.match_quantidade = (
        quantidade is not None and quantidade == item.quantidade
    )

    if class_validade == "vencida":
        salvar(StatusReconciliacao.DIVERGENCIA_VALIDADE)
        registrar_divergencia(
            transferencia,
            DivergenciaTransferencia.Tipo.VALIDADE,
            f"validade até {validade}",
            "validade vencida",
            severidade=DivergenciaTransferencia.Severidade.CRITICA,
            item=item,
        )
        return reconciliacao

    if class_validade == "critica":
        salvar(StatusReconciliacao.VALIDADE_CRITICA)
        registrar_divergencia(
            transferencia,
            DivergenciaTransferencia.Tipo.VALIDADE,
            f"validade {validade}",
            "validade crítica (≤ 30 dias)",
            severidade=DivergenciaTransferencia.Severidade.MEDIA,
            item=item,
        )
        return reconciliacao

    if reconciliacao.match_quantidade is False:
        salvar(StatusReconciliacao.DIVERGENCIA_QUANTIDADE)
        registrar_divergencia(
            transferencia,
            DivergenciaTransferencia.Tipo.QUANTIDADE,
            str(item.quantidade),
            str(quantidade),
            severidade=DivergenciaTransferencia.Severidade.MEDIA,
            item=item,
        )
        return reconciliacao

    salvar(StatusReconciliacao.CONFORME)
    return reconciliacao


def atualizar_status_itens_transferencia(transferencia):
    """Propaga o status final da reconciliação para os itens (listagem rápida)."""
    for item in transferencia.itens.select_related("reconciliacao"):
        status = StatusReconciliacao.NAO_FOTOGRAFADO
        if getattr(item, "reconciliacao", None) is not None:
            status = item.reconciliacao.status_final
        if item.status_reconciliacao != status:
            item.status_reconciliacao = status
            item.save(update_fields=["status_reconciliacao"])


def derivar_status_conferencia(transferencia, usuario=None):
    """Calcula o próximo estado da conferência a partir dos itens.

    - pendências de leitura (não fotografado/conferência manual) → EM_CONFERENCIA
    - divergências → DIVERGENCIA
    - tudo conforme → PRONTA_PARA_APROVACAO
    """
    criar_reconciliacoes_para_transferencia(transferencia)
    atualizar_status_itens_transferencia(transferencia)

    statuses = list(
        transferencia.itens.values_list("status_reconciliacao", flat=True)
    )
    if not statuses:
        return transferencia

    tem_divergencia = any(
        s
        in {
            StatusReconciliacao.DIVERGENCIA_PRODUTO,
            StatusReconciliacao.DIVERGENCIA_APRESENTACAO,
            StatusReconciliacao.DIVERGENCIA_LOTE,
            StatusReconciliacao.DIVERGENCIA_QUANTIDADE,
            StatusReconciliacao.DIVERGENCIA_VALIDADE,
            StatusReconciliacao.FOTO_INSUFICIENTE,
            StatusReconciliacao.POSSIVEL_DUPLICIDADE,
        }
        for s in statuses
    )
    pendentes = any(
        s
        in {
            StatusReconciliacao.NAO_FOTOGRAFADO,
            StatusReconciliacao.CONFERENCIA_MANUAL,
        }
        for s in statuses
    )
    divergencias_em_aberto = transferencia.divergencias.filter(
        status=DivergenciaTransferencia.StatusResolucao.PENDENTE
    ).exists()

    if tem_divergencia or divergencias_em_aberto:
        destino = Transferencia.StatusConferencia.DIVERGENCIA
    elif pendentes:
        destino = Transferencia.StatusConferencia.EM_CONFERENCIA
    else:
        destino = Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO

    if transferencia.status_conferencia != destino:
        atual = transferencia.status_conferencia
        if not pode_transicionar(atual, destino):
            # Caminho intermediário: bloqueios (divergência/pendência) saem
            # via EM_CONFERENCIA antes de avançar.
            if (
                transferencia.status_conferencia
                == Transferencia.StatusConferencia.DIVERGENCIA
                and pode_transicionar(
                    Transferencia.StatusConferencia.DIVERGENCIA,
                    Transferencia.StatusConferencia.EM_CONFERENCIA,
                )
            ):
                transicionar(
                    transferencia,
                    Transferencia.StatusConferencia.EM_CONFERENCIA,
                    usuario=usuario,
                    motivo="Reabertura após resolução de divergências.",
                )
        if not pode_transicionar(transferencia.status_conferencia, destino):
            raise ValueError(
                f"Caminho de estado inválido: {atual} → {destino}."
            )
        transicionar(transferencia, destino, usuario=usuario, motivo="Reconciliação automática.")
        sincronizar_status_operacional(transferencia)
    return transferencia


def resolver_divergencia(divergencia, usuario, resolucao):
    divergencia.status = DivergenciaTransferencia.StatusResolucao.RESOLVIDA
    divergencia.resolucao = resolucao
    divergencia.resolvida_por = usuario
    divergencia.resolvida_em = timezone.now()
    divergencia.save(update_fields=["status", "resolucao", "resolvida_por", "resolvida_em"])
    if divergencia.item is not None:
        atualizar_status_itens_transferencia(divergencia.transferencia)
    return divergencia


def integrar_ao_estoque(transferencia, usuario):
    """Após aprovação: cria lotes e movimentações de entrada (SKILL 25/26).

    Só executa quando a conferência está APROVADA; itens conformes viram
    lotes a partir do lote/validade observados na reconciliação.
    """
    from .models import Lote, MovimentacaoEstoque

    if transferencia.status_conferencia != Transferencia.StatusConferencia.APROVADA:
        raise ValueError(
            "Integração ao estoque exige transferência aprovada "
            f"(atual: {transferencia.status_conferencia})."
        )

    entradas = []
    for item in transferencia.itens.select_related("reconciliacao", "apresentacao"):
        reconciliacao = getattr(item, "reconciliacao", None)
        quantidade = (
            reconciliacao.quantidade_observada
            if reconciliacao and reconciliacao.quantidade_observada
            else item.quantidade
        )
        numero_lote = (
            reconciliacao.lote_observado
            if reconciliacao and reconciliacao.lote_observado
            else "SEM-LOTE-TRANSF"
        )
        data_validade = (
            reconciliacao.validade_observada
            if reconciliacao and reconciliacao.validade_observada
            else timezone.localdate() + timedelta(days=365)
        )
        lote, criado = Lote.objects.get_or_create(
            clinica=transferencia.clinica_destino,
            apresentacao=item.apresentacao,
            numero_lote=numero_lote,
            defaults={
                "data_validade": data_validade,
                "quantidade_inicial": quantidade,
                "quantidade_atual": quantidade,
            },
        )
        if not criado:
            lote.quantidade_atual += quantidade
            lote.quantidade_inicial += quantidade
            lote.data_validade = data_validade
            lote.save(update_fields=["quantidade_atual", "quantidade_inicial", "data_validade"])
        MovimentacaoEstoque.objects.create(
            clinica=transferencia.clinica_destino,
            lote=lote,
            tipo=MovimentacaoEstoque.TipoMovimentacao.ENTRADA,
            quantidade=quantidade,
            usuario=usuario,
            observacao=f"Conferência automatizada da transferência {transferencia.numero} (origem: {transferencia.clinica_origem.nome})",
        )
        item.quantidade_recebida += quantidade
        item.save(update_fields=["quantidade_recebida"])
        entradas.append(lote)

    transferencia.recebido_por = usuario
    transferencia.data_recebimento = timezone.now()
    transferencia.save(update_fields=["recebido_por", "data_recebimento"])
    return entradas