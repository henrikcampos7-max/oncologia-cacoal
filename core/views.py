import csv
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .forms import (
    LoteForm,
    MedicamentoApresentacaoForm,
    MovimentacaoEstoqueForm,
    PacienteForm,
    PeriodoForm,
    SessaoTratamentoForm,
)
from .models import (
    Apresentacao,
    Lote,
    Medicamento,
    MovimentacaoEstoque,
    Paciente,
    PerfilUsuario,
    RegistroAuditoria,
    SessaoTratamento,
)
from .services import processar_baixa_estoque_sessao, resumir_sessoes


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
        sessao.status = novo_status
        sessao.save()
        messages.success(request, f"Status da sessão atualizado para '{sessao.get_status_display()}'.")

        if novo_status == SessaoTratamento.Status.REALIZADA:
            _, msgs = processar_baixa_estoque_sessao(sessao, usuario=request.user)
            for msg in msgs:
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
            messages.success(request, "Paciente cadastrado. Revise o protocolo antes de usar operacionalmente.")
            return redirect("pacientes")
    contexto.update(
        form=form,
        pacientes=clinica.pacientes.select_related("protocolo").filter(ativo=True),
        pode_editar=pode_editar,
    )
    return render(request, "core/pacientes.html", contexto)


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
            form.save(clinica)
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
            messages.success(request, f"Lote {lote.numero_lote} cadastrado com sucesso.")
            return redirect("estoque")

        elif "salvar_movimentacao" in request.POST and form_movimentacao.is_valid():
            mov = form_movimentacao.save(commit=False)
            mov.clinica = clinica
            mov.usuario = request.user
            with transaction.atomic():
                lote = mov.lote
                if mov.tipo in [MovimentacaoEstoque.TipoMovimentacao.SAIDA, MovimentacaoEstoque.TipoMovimentacao.PERDA]:
                    qtd = -abs(mov.quantidade)
                else:
                    qtd = abs(mov.quantidade)
                mov.quantidade = qtd
                mov.save()
                lote.quantidade_atual = max(0, lote.quantidade_atual + qtd)
                lote.save()
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
    clinica = contexto["clinica"]
    if not clinica:
        return render(request, "core/compras.html", contexto)

    hoje = timezone.localdate()
    sessoes_proximas = clinica.sessoes.select_related("paciente", "protocolo").prefetch_related(
        "protocolo__itens__apresentacao__medicamento"
    ).filter(
        data_hora__date__range=(hoje, hoje + timedelta(days=30)),
        status__in=["agendada", "confirmada"],
    )

    linhas, _ = resumir_sessoes(sessoes_proximas)
    necessidades = []
    for linha in linhas:
        apresentacao = linha["apresentacao"]
        frascos_necessarios = linha["frascos"]
        estoque_disponivel = sum(
            l.quantidade_atual for l in apresentacao.lotes.filter(ativo=True)
        )
        falta = max(0, frascos_necessarios - estoque_disponivel)
        necessidades.append({
            "apresentacao": apresentacao,
            "necessario": frascos_necessarios,
            "estoque": estoque_disponivel,
            "falta": falta,
            "sugerido_compra": falta + 5 if falta > 0 else 0,
        })

    contexto.update(necessidades=necessidades)
    return render(request, "core/compras.html", contexto)


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


