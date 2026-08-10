from collections import defaultdict
from decimal import Decimal, ROUND_CEILING
from math import sqrt


def calcular_superficie_corporal(peso_kg, altura_cm):
    if peso_kg is None or altura_cm is None:
        return None
    peso, altura = Decimal(peso_kg), Decimal(altura_cm)
    if peso <= 0 or altura <= 0:
        return None
    return Decimal(str(sqrt(float(peso * altura / Decimal("3600"))))).quantize(
        Decimal("0.01")
    )


def calcular_dose_mg(dose_valor, tipo_dose, peso_kg=None, altura_cm=None):
    dose = Decimal(dose_valor)
    if tipo_dose == "fixa":
        return dose
    if tipo_dose == "mg_kg" and peso_kg is not None:
        return dose * Decimal(peso_kg)
    if tipo_dose == "mg_m2":
        superficie = calcular_superficie_corporal(peso_kg, altura_cm)
        if superficie is not None:
            return dose * superficie
    return None


def calcular_frascos(dose_total_mg, quantidade_mg):
    dose, quantidade = Decimal(dose_total_mg), Decimal(quantidade_mg)
    if dose < 0 or quantidade <= 0:
        raise ValueError("Dose e quantidade por frasco devem ser valores válidos.")
    return int((dose / quantidade).to_integral_value(rounding=ROUND_CEILING))


def numero_na_lista(texto, numero):
    try:
        valores = {int(item.strip()) for item in texto.split(",") if item.strip()}
    except ValueError:
        return False
    return int(numero) in valores


def resumir_sessoes(sessoes):
    acumulado = defaultdict(lambda: {"administracoes": 0, "dose_total": Decimal("0")})
    inconsistencias = []
    for sessao in sessoes:
        for item in sessao.protocolo.itens.select_related("apresentacao__medicamento"):
            if not numero_na_lista(item.ciclos, sessao.ciclo):
                continue
            if not numero_na_lista(item.dias_ciclo, sessao.dia_ciclo):
                continue
            dose = calcular_dose_mg(
                item.dose_valor,
                item.tipo_dose,
                sessao.paciente.peso_kg,
                sessao.paciente.altura_cm,
            )
            if dose is None:
                inconsistencias.append(
                    f"Dados insuficientes para calcular {item.apresentacao} na sessão {sessao.pk}."
                )
                continue
            chave = item.apresentacao_id
            acumulado[chave]["apresentacao"] = item.apresentacao
            acumulado[chave]["administracoes"] += 1
            acumulado[chave]["dose_total"] += dose

    linhas = []
    for dados in acumulado.values():
        apresentacao = dados["apresentacao"]
        linhas.append(
            {
                "medicamento": apresentacao.medicamento.nome,
                "apresentacao": apresentacao.descricao,
                "administracoes": dados["administracoes"],
                "dose_total": dados["dose_total"].quantize(Decimal("0.01")),
                "quantidade_mg": apresentacao.quantidade_mg,
                "frascos": calcular_frascos(dados["dose_total"], apresentacao.quantidade_mg),
            }
        )
    linhas.sort(key=lambda linha: (linha["medicamento"], linha["apresentacao"]))
    return linhas, inconsistencias


def processar_baixa_estoque_sessao(sessao, usuario=None):
    """
    Processa a baixa no estoque por FEFO (First Expired, First Out) para cada item do protocolo da sessão realizada.
    """
    from .models import Lote, MovimentacaoEstoque

    if sessao.movimentacoes_estoque.exists():
        return True, ["Baixa de estoque já havia sido realizada para esta sessão."]

    mensagens = []
    from django.db import transaction

    with transaction.atomic():
        for item in sessao.protocolo.itens.select_related("apresentacao"):
            if not numero_na_lista(item.ciclos, sessao.ciclo):
                continue
            if not numero_na_lista(item.dias_ciclo, sessao.dia_ciclo):
                continue

            dose = calcular_dose_mg(
                item.dose_valor,
                item.tipo_dose,
                sessao.paciente.peso_kg,
                sessao.paciente.altura_cm,
            )
            if dose is None or dose == 0:
                continue

            frascos_necessarios = calcular_frascos(dose, item.apresentacao.quantidade_mg)
            if frascos_necessarios <= 0:
                continue

            lotes_disponiveis = Lote.objects.filter(
                clinica=sessao.clinica,
                apresentacao=item.apresentacao,
                ativo=True,
                quantidade_atual__gt=0,
            ).order_by("data_validade")

            restante = frascos_necessarios
            for lote in lotes_disponiveis:
                if restante <= 0:
                    break
                deduzir = min(lote.quantidade_atual, restante)
                lote.quantidade_atual -= deduzir
                lote.save()
                restante -= deduzir

                MovimentacaoEstoque.objects.create(
                    clinica=sessao.clinica,
                    lote=lote,
                    tipo=MovimentacaoEstoque.TipoMovimentacao.SAIDA,
                    quantidade=-deduzir,
                    sessao=sessao,
                    usuario=usuario,
                    observacao=f"Aplicação realizada — Paciente: {sessao.paciente.nome}",
                )

            if restante > 0:
                mensagens.append(
                    f"Estoque insuficiente para {item.apresentacao.descricao}. Faltaram {restante} frascos."
                )

    return True, mensagens

