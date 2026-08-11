import csv
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .forms import (
    ApresentacaoForm,
    ItemProtocoloForm,
    LoteForm,
    MedicamentoApresentacaoForm,
    MedicamentoForm,
    MovimentacaoEstoqueForm,
    PacienteForm,
    PeriodoForm,
    ProtocoloForm,
    SessaoTratamentoForm,
)
from .models import (
    Apresentacao,
    ItemPedidoCompra,
    ItemProtocolo,
    Lote,
    Medicamento,
    MovimentacaoEstoque,
    Paciente,
    PedidoCompra,
    PerfilUsuario,
    Protocolo,
    RegistroAuditoria,
    SessaoTratamento,
)
from .services import (
    calcular_sugestao_compras,
    processar_baixa_estoque_sessao,
    registrar_auditoria,
    resumir_sessoes,
)


@never_cache
@require_GET
def health(request):
    """Confirma que a aplicação respondeu; não consulta nem expõe dados."""
    return JsonResponse({"status": "ok", "sistema": "Oncologia Cacoal"})


def solicitar_acesso(request):
    return render(request, "core/solicitar_acesso.html")


def _perfil(request):
    if request.user.is_superuser:
        return PerfilUsuario.objects.filter(usuario=request.user, ativo=True).select_related("clinica").first()
    return PerfilUsuario.objects.filter(usuario=request.user, ativo=True).select_related("clinica").first()


def _contexto(request, titulo):
    perfil = _perfil(request)
    return {"titulo": titulo, "perfil": perfil, "clinica": perfil.clinica if perfil else None}


def _pode_editar(perfil, papeis):
    return bool(perfil and perfil.papel in papeis)


@login_required
def dashboard(request):
    contexto = _contexto(request, "Painel")
    clinica = contexto["clinica"]
    if clinica:
        hoje = timezone.localdate()
        contexto.update(
            pacientes_total=clinica.pacientes.filter(ativo=True).count(),
            medicamentos_total=clinica.medicamentos.filter(ativo=True).count(),
            aplicacoes_7_dias=clinica.sessoes.filter(
                data_hora__date__range=(hoje, hoje + timedelta(days=7)),
                status__in=["agendada", "confirmada"],
            ).count(),
            proximas_sessoes=clinica.sessoes.select_related("paciente", "protocolo")
            .filter(data_hora__gte=timezone.now())[:6],
        )
    return render(request, "core/dashboard.html", contexto)


def _sessoes_filtradas(request, clinica):
    data_texto = request.GET.get("data") or timezone.localdate().isoformat()
    try:
        data_filtro = date.fromisoformat(data_texto)
    except ValueError:
        data_filtro = timezone.localdate()
    sessoes = clinica.sessoes.select_related("paciente", "protocolo").filter(
        data_hora__date=data_filtro
    )
    busca = request.GET.get("paciente", "").strip()
    protocolo = request.GET.get("protocolo", "").strip()
    if busca:
        sessoes = sessoes.filter(paciente__nome__icontains=busca)
    if protocolo:
        sessoes = sessoes.filter(protocolo__nome__icontains=protocolo)
    return sessoes, data_filtro, busca, protocolo


@login_required
def agenda(request):
    contexto = _contexto(request, "Agenda de Tratamentos")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return render(request, "core/agenda.html", contexto)
    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO, PerfilUsuario.Papel.ENFERMAGEM}
    )
    form = SessaoTratamentoForm(request.POST or None, clinica=clinica)
    if request.method == "POST":
        if not pode_editar:
            return HttpResponse("Perfil sem permissão para agendar.", status=403)
        if form.is_valid():
            sessao = form.save(commit=False)
            sessao.clinica = clinica
            if sessao.paciente.clinica_id != clinica.id or sessao.protocolo.clinica_id != clinica.id:
                return HttpResponse("Dados fora da clínica selecionada.", status=403)
            try:
                with transaction.atomic():
                    sessao.save()
            except IntegrityError:
                form.add_error(None, "Já existe uma aplicação igual para este paciente, data, ciclo e dia.")
            else:
                messages.success(request, "Próximo tratamento registrado para revisão.")
                return redirect("agenda")
    sessoes, data_filtro, busca, protocolo = _sessoes_filtradas(request, clinica)
    contexto.update(
        form=form,
        sessoes=sessoes,
        data_filtro=data_filtro,
        busca=busca,
        protocolo_filtro=protocolo,
        pode_editar=pode_editar,
    )
    return render(request, "core/agenda.html", contexto)


@login_required
def agenda_csv(request):
    perfil = _perfil(request)
    if not perfil:
        return HttpResponse("Usuário sem clínica vinculada.", status=403)
    sessoes, _, _, _ = _sessoes_filtradas(request, perfil.clinica)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="agenda-oncologia-cacoal.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Hora", "Paciente", "Protocolo", "Ciclo", "Dia", "Status"])
    for sessao in sessoes:
        writer.writerow(
            [
                timezone.localtime(sessao.data_hora).strftime("%H:%M"),
                sessao.paciente.nome,
                sessao.protocolo.nome,
                sessao.ciclo,
                sessao.dia_ciclo,
                sessao.get_status_display(),
            ]
        )
    return response


@login_required
def agenda_impressao(request):
    perfil = _perfil(request)
    if not perfil:
        return HttpResponse("Usuário sem clínica vinculada.", status=403)
    sessoes, data_filtro, _, _ = _sessoes_filtradas(request, perfil.clinica)
    return render(
        request,
        "core/agenda_impressao.html",
        {"sessoes": sessoes, "data_filtro": data_filtro, "clinica": perfil.clinica},
    )


@login_required
def atualizar_status_sessao(request, pk):
    perfil = _perfil(request)
    if not perfil or not _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO, PerfilUsuario.Papel.ENFERMAGEM}
    ):
        return HttpResponse("Perfil sem permissão.", status=403)

    sessao = SessaoTratamento.objects.filter(pk=pk, clinica=perfil.clinica).first()
    if not sessao:
        return HttpResponse("Sessão não encontrada.", status=404)

    novo_status = request.POST.get("status")
    if novo_status in dict(SessaoTratamento.Status.choices):
        mensagens = []
        with transaction.atomic():
            if novo_status == SessaoTratamento.Status.REALIZADA:
                _, mensagens = processar_baixa_estoque_sessao(sessao, usuario=request.user)
            sessao.status = novo_status
            sessao.save()
        messages.success(request, f"Status da sessão atualizado para '{sessao.get_status_display()}'.")
        registrar_auditoria(
            sessao.clinica,
            request.user,
            "Alteração de status de sessão",
            f"Sessão {sessao.pk} do paciente {sessao.paciente.nome} marcada como {sessao.get_status_display()}.",
            request=request,
        )
        for msg in mensagens:
            messages.warning(request, msg)

    return redirect("agenda")



@login_required
def pacientes(request):
    contexto = _contexto(request, "Cadastro de Pacientes e Tratamentos")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return render(request, "core/pacientes.html", contexto)
    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO, PerfilUsuario.Papel.ENFERMAGEM}
    )
    form = PacienteForm(request.POST or None, clinica=clinica)
    if request.method == "POST":
        if not pode_editar:
            return HttpResponse("Perfil sem permissão para cadastrar pacientes.", status=403)
        if form.is_valid():
            paciente = form.save(commit=False)
            paciente.clinica = clinica
            paciente.save()
            registrar_auditoria(
                clinica,
                request.user,
                "Cadastro de paciente",
                f"Paciente {paciente.nome} criado (protocolo: {paciente.protocolo or 'não definido'}).",
                request=request,
            )
            messages.success(request, "Paciente cadastrado. Revise o protocolo antes de usar operacionalmente.")
            return redirect("pacientes")
    contexto.update(
        form=form,
        pacientes=clinica.pacientes.select_related("protocolo").filter(ativo=True),
        pode_editar=pode_editar,
    )
    return render(request, "core/pacientes.html", contexto)


@login_required
def editar_paciente(request, pk):
    contexto = _contexto(request, "Editar Paciente")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return HttpResponse("Clínica não encontrada.", status=404)
    
    paciente = Paciente.objects.filter(pk=pk, clinica=clinica).first()
    if not paciente:
        return HttpResponse("Paciente não encontrado.", status=404)
    
    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO, PerfilUsuario.Papel.ENFERMAGEM}
    )
    
    if not pode_editar:
        return HttpResponse("Perfil sem permissão para editar pacientes.", status=403)
    
    form = PacienteForm(request.POST or None, instance=paciente, clinica=clinica)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            registrar_auditoria(
                clinica,
                request.user,
                "Edição de paciente",
                f"Paciente {paciente.nome} atualizado.",
                request=request,
            )
            messages.success(request, "Paciente atualizado com sucesso.")
            return redirect("pacientes")
    
    contexto.update(form=form, paciente=paciente)
    return render(request, "core/editar_paciente.html", contexto)


@login_required
def medicamentos(request):
    contexto = _contexto(request, "Cadastro de Medicamentos")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return render(request, "core/medicamentos.html", contexto)
    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )
    form = MedicamentoApresentacaoForm(request.POST or None)
    if request.method == "POST":
        if not pode_editar:
            return HttpResponse("Perfil sem permissão para cadastrar medicamentos.", status=403)
        if form.is_valid():
            apresentacao = form.save(clinica)
            registrar_auditoria(
                clinica,
                request.user,
                "Cadastro de medicamento/apresentação",
                f"Apresentação {apresentacao.descricao} ({apresentacao.medicamento.nome}) cadastrada.",
                request=request,
            )
            messages.success(request, "Apresentação cadastrada para revisão farmacêutica.")
            return redirect("medicamentos")
    apresentacoes = (
        clinica.medicamentos.filter(ativo=True)
        .prefetch_related("apresentacoes")
        .order_by("nome")
    )
    contexto.update(form=form, medicamentos=apresentacoes, pode_editar=pode_editar)
    return render(request, "core/medicamentos.html", contexto)


@login_required
def editar_medicamento(request, pk):
    contexto = _contexto(request, "Editar Medicamento")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return HttpResponse("Clínica não encontrada.", status=404)
    
    medicamento = Medicamento.objects.filter(pk=pk, clinica=clinica).first()
    if not medicamento:
        return HttpResponse("Medicamento não encontrado.", status=404)
    
    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )
    
    if not pode_editar:
        return HttpResponse("Perfil sem permissão para editar medicamentos.", status=403)
    
    form = MedicamentoForm(request.POST or None, instance=medicamento)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            registrar_auditoria(
                clinica,
                request.user,
                "Edição de medicamento",
                f"Medicamento {medicamento.nome} atualizado.",
                request=request,
            )
            messages.success(request, "Medicamento atualizado com sucesso.")
            return redirect("medicamentos")
    
    contexto.update(form=form, medicamento=medicamento)
    return render(request, "core/editar_medicamento.html", contexto)


@login_required
def editar_apresentacao(request, pk):
    contexto = _contexto(request, "Editar Apresentação")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return HttpResponse("Clínica não encontrada.", status=404)
    
    apresentacao = Apresentacao.objects.filter(pk=pk, medicamento__clinica=clinica).first()
    if not apresentacao:
        return HttpResponse("Apresentação não encontrada.", status=404)
    
    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )
    
    if not pode_editar:
        return HttpResponse("Perfil sem permissão para editar apresentações.", status=403)
    
    form = ApresentacaoForm(request.POST or None, instance=apresentacao)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            registrar_auditoria(
                clinica,
                request.user,
                "Edição de apresentação",
                f"Apresentação {apresentacao.descricao} ({apresentacao.medicamento.nome}) atualizada.",
                request=request,
            )
            messages.success(request, "Apresentação atualizada com sucesso.")
            return redirect("medicamentos")
    
    contexto.update(form=form, apresentacao=apresentacao)
    return render(request, "core/editar_apresentacao.html", contexto)


@login_required
def protocolos(request):
    contexto = _contexto(request, "Protocolos Terapêuticos")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return render(request, "core/protocolos.html", contexto)
    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )
    form = ProtocoloForm(request.POST or None)
    if request.method == "POST":
        if not pode_editar:
            return HttpResponse("Perfil sem permissão para cadastrar protocolos.", status=403)
        if form.is_valid():
            protocolo = form.save(commit=False)
            protocolo.clinica = clinica
            protocolo.save()
            registrar_auditoria(
                clinica,
                request.user,
                "Cadastro de protocolo",
                f"Protocolo {protocolo.nome} criado (diagnóstico: {protocolo.diagnostico_referencia or 'não informado'}).",
                request=request,
            )
            messages.success(request, "Protocolo criado. Adicione os itens (medicamentos) abaixo.")
            return redirect("editar_protocolo", pk=protocolo.pk)
    protocolos = (
        clinica.protocolos.filter(ativo=True)
        .prefetch_related("itens__apresentacao__medicamento")
        .order_by("nome")
    )
    contexto.update(form=form, protocolos=protocolos, pode_editar=pode_editar)
    return render(request, "core/protocolos.html", contexto)


@login_required
def editar_protocolo(request, pk):
    contexto = _contexto(request, "Editar Protocolo")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return HttpResponse("Clínica não encontrada.", status=404)
    protocolo = Protocolo.objects.filter(pk=pk, clinica=clinica).first()
    if not protocolo:
        return HttpResponse("Protocolo não encontrado.", status=404)
    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )
    if not pode_editar:
        return HttpResponse("Perfil sem permissão para editar protocolos.", status=403)

    form = ProtocoloForm(request.POST or None, instance=protocolo)
    form_item = ItemProtocoloForm(request.POST or None, clinica=clinica, prefix="item")

    if request.method == "POST":
        if "salvar_protocolo" in request.POST and form.is_valid():
            form.save()
            registrar_auditoria(
                clinica,
                request.user,
                "Edição de protocolo",
                f"Protocolo {protocolo.nome} atualizado.",
                request=request,
            )
            messages.success(request, "Protocolo atualizado com sucesso.")
            return redirect("editar_protocolo", pk=protocolo.pk)
        if "salvar_item" in request.POST and form_item.is_valid():
            item = form_item.save(commit=False)
            item.protocolo = protocolo
            item.save()
            registrar_auditoria(
                clinica,
                request.user,
                "Adição de item de protocolo",
                f"Item {item.apresentacao} adicionado ao protocolo {protocolo.nome}.",
                request=request,
            )
            messages.success(request, f"Item {item.apresentacao} adicionado ao protocolo.")
            return redirect("editar_protocolo", pk=protocolo.pk)

    itens = protocolo.itens.select_related("apresentacao__medicamento")
    contexto.update(form=form, form_item=form_item, protocolo=protocolo, itens=itens)
    return render(request, "core/editar_protocolo.html", contexto)


@login_required
def remover_item_protocolo(request, pk):
    perfil = _perfil(request)
    if not perfil or not _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    ):
        return HttpResponse("Perfil sem permissão.", status=403)
    item = ItemProtocolo.objects.filter(pk=pk, protocolo__clinica=perfil.clinica).first()
    if request.method == "POST" and item:
        protocolo = item.protocolo
        descricao = str(item.apresentacao)
        item.delete()
        registrar_auditoria(
            perfil.clinica,
            request.user,
            "Remoção de item de protocolo",
            f"Item {descricao} removido do protocolo {protocolo.nome}.",
            request=request,
        )
        messages.success(request, "Item removido do protocolo.")
        return redirect("editar_protocolo", pk=protocolo.pk)
    return HttpResponse("Requisição inválida.", status=400)


@login_required
def quantitativo(request):
    contexto = _contexto(request, "Quantitativo e Previsão de Medicamentos")
    clinica = contexto["clinica"]
    hoje = timezone.localdate()
    form = PeriodoForm(
        request.GET or {"data_inicial": hoje, "data_final": hoje + timedelta(days=14)}
    )
    linhas, inconsistencias = [], []
    if clinica and form.is_valid():
        sessoes = clinica.sessoes.select_related("paciente", "protocolo").prefetch_related(
            "protocolo__itens__apresentacao__medicamento"
        ).filter(
            data_hora__date__range=(
                form.cleaned_data["data_inicial"],
                form.cleaned_data["data_final"],
            ),
            status__in=["agendada", "confirmada"],
        )
        linhas, inconsistencias = resumir_sessoes(sessoes)
    contexto.update(
        form=form,
        linhas=linhas,
        inconsistencias=inconsistencias,
        total_frascos=sum(linha["frascos"] for linha in linhas),
    )
    return render(request, "core/quantitativo.html", contexto)


MODULOS = {
    "transferencias": ("Transferências", "Transferências entre unidades com rastreabilidade."),
    "importacoes": ("Importações", "Mapeamento, prévia, validação e conciliação de arquivos."),
    "auditoria": ("Usuários, Permissões e Auditoria", "Perfis, acessos e trilha de auditoria."),
}


@login_required
def modulo_planejado(request, slug):
    titulo, descricao = MODULOS.get(slug, ("Módulo planejado", "Funcionalidade em planejamento."))
    contexto = _contexto(request, titulo)
    contexto["descricao_modulo"] = descricao
    return render(request, "core/modulo_planejado.html", contexto)


@login_required
def estoque(request):
    contexto = _contexto(request, "Estoque, Lotes e Validades")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return render(request, "core/estoque.html", contexto)

    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )

    form_lote = LoteForm(request.POST or None, clinica=clinica, prefix="lote")
    form_movimentacao = MovimentacaoEstoqueForm(request.POST or None, clinica=clinica, prefix="mov")

    if request.method == "POST" and pode_editar:
        if "salvar_lote" in request.POST and form_lote.is_valid():
            with transaction.atomic():
                lote = form_lote.save(commit=False)
                lote.clinica = clinica
                lote.quantidade_atual = lote.quantidade_inicial
                lote.save()

                if lote.quantidade_inicial > 0:
                    MovimentacaoEstoque.objects.create(
                        clinica=clinica,
                        lote=lote,
                        tipo=MovimentacaoEstoque.TipoMovimentacao.ENTRADA,
                        quantidade=lote.quantidade_inicial,
                        usuario=request.user,
                        observacao="Carga inicial de estoque",
                    )
            registrar_auditoria(
                clinica,
                request.user,
                "Cadastro de lote",
                f"Lote {lote.numero_lote} ({lote.apresentacao}) com {lote.quantidade_inicial} frascos, validade {lote.data_validade:%d/%m/%Y}.",
                request=request,
            )
            messages.success(request, f"Lote {lote.numero_lote} cadastrado com sucesso.")
            return redirect("estoque")

        elif "salvar_movimentacao" in request.POST and form_movimentacao.is_valid():
            mov = form_movimentacao.save(commit=False)
            mov.clinica = clinica
            mov.usuario = request.user
            with transaction.atomic():
                lote = mov.lote
                if mov.tipo == MovimentacaoEstoque.TipoMovimentacao.RESERVA:
                    mov.quantidade = abs(mov.quantidade)
                    mov.save()
                    registrar_auditoria(
                        clinica,
                        request.user,
                        "Reserva de estoque",
                        f"Reserva de {mov.quantidade} frascos do lote {lote.numero_lote}.",
                        request=request,
                    )
                    messages.success(
                        request,
                        f"Reserva de {mov.quantidade} frascos registrada para o lote {lote.numero_lote}.",
                    )
                    return redirect("estoque")
                if mov.tipo in [MovimentacaoEstoque.TipoMovimentacao.SAIDA, MovimentacaoEstoque.TipoMovimentacao.PERDA]:
                    qtd = -abs(mov.quantidade)
                elif mov.tipo == MovimentacaoEstoque.TipoMovimentacao.ENTRADA:
                    qtd = abs(mov.quantidade)
                else:
                    qtd = mov.quantidade
                mov.quantidade = qtd
                mov.save()
                lote.quantidade_atual = max(0, lote.quantidade_atual + qtd)
                lote.save()
            registrar_auditoria(
                clinica,
                request.user,
                "Movimentação de estoque",
                f"{mov.get_tipo_display()} de {abs(qtd)} frascos do lote {lote.numero_lote}. Saldo atual: {lote.quantidade_atual}.",
                request=request,
            )
            messages.success(request, f"Movimentação registrada para o lote {lote.numero_lote}.")
            return redirect("estoque")

    lotes = (
        clinica.lotes.filter(ativo=True)
        .select_related("apresentacao__medicamento")
        .order_by("data_validade")
    )
    movimentacoes = (
        clinica.movimentacoes_estoque.select_related(
            "lote__apresentacao__medicamento", "usuario"
        ).order_by("-data_hora")[:20]
    )

    contexto.update(
        form_lote=form_lote,
        form_movimentacao=form_movimentacao,
        lotes=lotes,
        movimentacoes=movimentacoes,
        pode_editar=pode_editar,
    )
    return render(request, "core/estoque.html", contexto)


@login_required
def alertas(request):
    contexto = _contexto(request, "Alertas e Notificações de Estoque")
    clinica = contexto["clinica"]
    if not clinica:
        return render(request, "core/alertas.html", contexto)

    lotes = clinica.lotes.filter(ativo=True).select_related("apresentacao__medicamento")
    
    vencidos = [l for l in lotes if l.status_validade == "vencido"]
    criticos_validade = [l for l in lotes if l.status_validade == "critico"]
    alertas_validade = [l for l in lotes if l.status_validade == "alerta"]
    estoque_baixo = [l for l in lotes if l.status_estoque in ["baixo", "esgotado"]]

    contexto.update(
        vencidos=vencidos,
        criticos_validade=criticos_validade,
        alertas_validade=alertas_validade,
        estoque_baixo=estoque_baixo,
        total_alertas=len(vencidos) + len(criticos_validade) + len(estoque_baixo),
    )
    return render(request, "core/alertas.html", contexto)


@login_required
def compras(request):
    contexto = _contexto(request, "Pedidos, Compras e Recebimentos")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return render(request, "core/compras.html", contexto)

    pode_criar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )
    necessidades = calcular_sugestao_compras(clinica)

    if request.method == "POST" and pode_criar:
        if "criar_pedido" in request.POST:
            itens_selecionados = []
            for chave, quantidade in request.POST.items():
                if not chave.startswith("qtd_") or not quantidade:
                    continue
                apresentacao_id = chave.removeprefix("qtd_")
                try:
                    quantidade_int = int(quantidade)
                except ValueError:
                    continue
                if quantidade_int <= 0:
                    continue
                apresentacao = Apresentacao.objects.filter(
                    pk=apresentacao_id, medicamento__clinica=clinica, ativa=True
                ).first()
                if apresentacao:
                    itens_selecionados.append((apresentacao, quantidade_int))
            if itens_selecionados:
                with transaction.atomic():
                    pedido = PedidoCompra.objects.create(
                        clinica=clinica,
                        solicitante=request.user,
                        fornecedor=request.POST.get("fornecedor", ""),
                        observacao=request.POST.get("observacao", ""),
                    )
                    pedido.numero = pedido.gerar_numero()
                    pedido.save(update_fields=["numero"])
                    for apresentacao, quantidade in itens_selecionados:
                        ItemPedidoCompra.objects.create(
                            pedido=pedido,
                            apresentacao=apresentacao,
                            quantidade=quantidade,
                        )
                    registrar_auditoria(
                        clinica,
                        request.user,
                        "Criação de pedido de compra",
                        f"Pedido {pedido.numero} criado com {len(itens_selecionados)} item(ns).",
                        request=request,
                    )
                messages.success(request, f"Pedido {pedido.numero} criado em rascunho.")
                return redirect("detalhe_pedido", pk=pedido.pk)
            messages.error(request, "Selecione ao menos um item com quantidade válida.")
            return redirect("compras")

    pedidos = (
        clinica.pedidos_compra.select_related("solicitante")
        .prefetch_related("itens__apresentacao__medicamento")[:20]
    )
    contexto.update(
        necessidades=necessidades,
        pedidos=pedidos,
        pode_criar=pode_criar,
    )
    return render(request, "core/compras.html", contexto)


@login_required
def detalhe_pedido(request, pk):
    contexto = _contexto(request, "Detalhe do Pedido de Compra")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return HttpResponse("Clínica não encontrada.", status=404)

    pedido = PedidoCompra.objects.filter(pk=pk, clinica=clinica).first()
    if not pedido:
        return HttpResponse("Pedido não encontrado.", status=404)

    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )
    pode_aprovar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.GESTOR}
    )

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "enviar" and pode_editar and pedido.status == PedidoCompra.Status.RASCUNHO:
            pedido.status = PedidoCompra.Status.PENDENTE
            pedido.save(update_fields=["status"])
            registrar_auditoria(
                clinica, request.user, "Envio de pedido para aprovação",
                f"Pedido {pedido.numero} enviado para aprovação.", request=request,
            )
            messages.success(request, "Pedido enviado para aprovação.")
            return redirect("detalhe_pedido", pk=pedido.pk)

        if acao == "aprovar" and pode_aprovar and pedido.status == PedidoCompra.Status.PENDENTE:
            pedido.status = PedidoCompra.Status.APROVADO
            pedido.aprovador = request.user
            pedido.data_aprovacao = timezone.now()
            pedido.save(update_fields=["status", "aprovador", "data_aprovacao"])
            registrar_auditoria(
                clinica, request.user, "Aprovação de pedido de compra",
                f"Pedido {pedido.numero} aprovado.", request=request,
            )
            messages.success(request, "Pedido aprovado.")
            return redirect("detalhe_pedido", pk=pedido.pk)

        if acao == "cancelar" and pode_editar and pedido.status in [
            PedidoCompra.Status.RASCUNHO, PedidoCompra.Status.PENDENTE, PedidoCompra.Status.APROVADO,
        ]:
            pedido.status = PedidoCompra.Status.CANCELADO
            pedido.save(update_fields=["status"])
            registrar_auditoria(
                clinica, request.user, "Cancelamento de pedido de compra",
                f"Pedido {pedido.numero} cancelado.", request=request,
            )
            messages.success(request, "Pedido cancelado.")
            return redirect("detalhe_pedido", pk=pedido.pk)

        if acao == "receber" and pode_editar and pedido.status == PedidoCompra.Status.APROVADO:
            erros = []
            itens_nao_recebidos = pedido.itens.select_related("apresentacao").filter(
                quantidade_recebida__lt=F("quantidade")
            )
            with transaction.atomic():
                for item in itens_nao_recebidos:
                    qtd_recebida = request.POST.get(f"recebido_{item.pk}")
                    numero_lote = request.POST.get(f"lote_{item.pk}", "").strip()
                    validade = request.POST.get(f"validade_{item.pk}", "").strip()
                    try:
                        qtd_recebida = int(qtd_recebida) if qtd_recebida else 0
                    except ValueError:
                        qtd_recebida = 0
                    if qtd_recebida <= 0:
                        continue
                    if not numero_lote or not validade:
                        erros.append(f"{item.apresentacao}: informe lote e validade para receber.")
                        continue
                    try:
                        data_validade = date.fromisoformat(validade)
                    except ValueError:
                        erros.append(f"{item.apresentacao}: validade inválida ({validade}).")
                        continue
                    lote, criado = Lote.objects.get_or_create(
                        clinica=clinica,
                        apresentacao=item.apresentacao,
                        numero_lote=numero_lote,
                        defaults={"data_validade": data_validade, "quantidade_inicial": qtd_recebida, "quantidade_atual": qtd_recebida},
                    )
                    lote.data_validade = data_validade
                    if criado:
                        lote.save(update_fields=["data_validade"])
                    else:
                        lote.quantidade_atual += qtd_recebida
                        lote.save(update_fields=["quantidade_atual", "data_validade"])
                    MovimentacaoEstoque.objects.create(
                        clinica=clinica,
                        lote=lote,
                        tipo=MovimentacaoEstoque.TipoMovimentacao.ENTRADA,
                        quantidade=qtd_recebida,
                        usuario=request.user,
                        observacao=f"Recebimento do pedido {pedido.numero}",
                    )
                    item.quantidade_recebida += qtd_recebida
                    item.save(update_fields=["quantidade_recebida"])
                if not erros:
                    restantes = pedido.itens.filter(quantidade_recebida__lt=F("quantidade")).exists()
                    if not restantes:
                        pedido.status = PedidoCompra.Status.RECEBIDO
                        pedido.data_recebimento = timezone.now()
                        pedido.save(update_fields=["status", "data_recebimento"])
                    registrar_auditoria(
                        clinica, request.user, "Recebimento de pedido de compra",
                        f"Recebimento registrado para o pedido {pedido.numero}.",
                        request=request,
                    )
                    messages.success(request, "Recebimento registrado. Lotes criados no estoque.")
            for erro in erros:
                messages.error(request, erro)
            return redirect("detalhe_pedido", pk=pedido.pk)

    itens = pedido.itens.select_related("apresentacao__medicamento")
    contexto.update(
        pedido=pedido,
        itens=itens,
        pode_editar=pode_editar,
        pode_aprovar=pode_aprovar,
    )
    return render(request, "core/detalhe_pedido.html", contexto)


@login_required
def relatorios(request):
    contexto = _contexto(request, "Relatórios e Indicadores Administrativos")
    clinica = contexto["clinica"]
    if clinica:
        lotes = clinica.lotes.filter(ativo=True)
        total_lotes = lotes.count()
        total_frascos_estoque = sum(l.quantidade_atual for l in lotes)
        pacientes_ativos = clinica.pacientes.filter(ativo=True).count()
        sessoes_realizadas_mes = clinica.sessoes.filter(
            data_hora__month=timezone.localdate().month,
            status="realizada",
        ).count()
        contexto.update(
            total_lotes=total_lotes,
            total_frascos_estoque=total_frascos_estoque,
            pacientes_ativos=pacientes_ativos,
            sessoes_realizadas_mes=sessoes_realizadas_mes,
        )
    return render(request, "core/relatorios.html", contexto)


@login_required
def auditoria(request):
    contexto = _contexto(request, "Usuários, Permissões e Trilhas de Auditoria")
    clinica = contexto["clinica"]
    if not clinica:
        return render(request, "core/auditoria.html", contexto)

    registros = clinica.auditorias.select_related("usuario").order_by("-data_hora")[:50]
    perfis = clinica.perfis.select_related("usuario").order_by("usuario__username")

    contexto.update(registros=registros, perfis=perfis)
    return render(request, "core/auditoria.html", contexto)


