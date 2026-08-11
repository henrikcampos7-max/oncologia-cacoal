import csv
import os
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .forms import (
    ApresentacaoForm,
    ImportacaoArquivoForm,
    ItemProtocoloForm,
    LoteForm,
    MedicamentoApresentacaoForm,
    MedicamentoForm,
    MovimentacaoEstoqueForm,
    PacienteForm,
    PeriodoForm,
    ProtocoloForm,
    SessaoTratamentoForm,
    SobraRealForm,
    SolicitacaoAcessoForm,
)
from .models import (
    Apresentacao,
    Clinica,
    DivergenciaTransferencia,
    ExtracaoEvidencia,
    ItemPedidoCompra,
    ItemProtocolo,
    ItemTransferencia,
    Lote,
    Medicamento,
    MovimentacaoEstoque,
    Paciente,
    PedidoCompra,
    PerfilUsuario,
    Protocolo,
    RegistroAuditoria,
    SessaoTratamento,
    SobraReal,
    SolicitacaoAcesso,
    Transferencia,
    TransferenciaEvidencia,
)
from .services import (
    calcular_estoque_disponivel_apresentacao,
    calcular_sugestao_compras,
    coletar_alertas_estoque,
    enviar_alertas_por_email,
    importar_gmed,
    importar_medicamentos,
    importar_transferencia_pdf,
    importar_transferencias,
    inspecionar_importacao,
    processar_baixa_estoque_sessao,
    processar_saida_lotes,
    registrar_auditoria,
    resumir_sessoes,
    sobras_reais_expiradas,
    sobras_reais_validas,
)
from .reconciliacao import (
    atualizar_status_itens_transferencia,
    derivar_status_conferencia,
    integrar_ao_estoque,
    reconciliar_item,
)
from .vision import processar_evidencia, resumo_aprovacao
from .conferencia import (
    sincronizar_status_operacional,
    transicionar,
)


@never_cache
@require_GET
def health(request):
    """Confirma que a aplicação respondeu; não consulta nem expõe dados."""
    return JsonResponse({"status": "ok", "sistema": "Oncologia Cacoal"})


def solicitar_acesso(request):
    form = SolicitacaoAcessoForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Solicitação enviada. Um administrador analisará e criará seu acesso.",
            )
            return redirect("solicitar_acesso")
    return render(request, "core/solicitar_acesso.html", {"form": form})


@login_required
def solicitacoes_acesso(request):
    perfil = _perfil(request)
    if not perfil or perfil.papel != PerfilUsuario.Papel.ADMINISTRADOR:
        return HttpResponse("Perfil sem permissão para analisar solicitações.", status=403)

    if request.method == "POST":
        solicitacao = SolicitacaoAcesso.objects.filter(
            pk=request.POST.get("pk"), status=SolicitacaoAcesso.Status.PENDENTE
        ).first()
        acao = request.POST.get("acao")
        if solicitacao:
            if acao == "aprovar":
                senha_temporaria = get_random_string(length=15)
                username = solicitacao.email.split("@")[0][:150]
                username_base, contador = username, 1
                while get_user_model().objects.filter(username__iexact=username).exists():
                    contador += 1
                    username = f"{username_base}{contador}"
                usuario, _ = get_user_model().objects.get_or_create(
                    email=solicitacao.email.lower(),
                    defaults={"username": username},
                )
                if not usuario.username:
                    usuario.username = username
                usuario.set_password(senha_temporaria)
                usuario.save()
                PerfilUsuario.objects.update_or_create(
                    usuario=usuario,
                    defaults={"clinica": solicitacao.clinica or perfil.clinica, "papel": solicitacao.papel_solicitado, "ativo": True},
                )
                solicitacao.status = SolicitacaoAcesso.Status.APROVADA
                solicitacao.analisado_por = request.user
                solicitacao.data_analise = timezone.now()
                solicitacao.save()
                registrar_auditoria(
                    perfil.clinica or solicitacao.clinica,
                    request.user,
                    "Aprovação de solicitação de acesso",
                    f"Acesso aprovado para {solicitacao.nome_completo} ({solicitacao.email}).",
                    request=request,
                )
                messages.success(
                    request,
                    f"Acesso aprovado para {solicitacao.nome_completo}. "
                    f"Usuário: {usuario.username} — Senha temporária: {senha_temporaria} "
                    "(compartilhe com o solicitante; ele poderá alterar depois).",
                )
            elif acao == "rejeitar":
                solicitacao.status = SolicitacaoAcesso.Status.REJEITADA
                solicitacao.analisado_por = request.user
                solicitacao.data_analise = timezone.now()
                solicitacao.save()
                registrar_auditoria(
                    perfil.clinica or solicitacao.clinica,
                    request.user,
                    "Rejeição de solicitação de acesso",
                    f"Solicitação de {solicitacao.nome_completo} ({solicitacao.email}) rejeitada.",
                    request=request,
                )
                messages.success(request, "Solicitação rejeitada.")
        return redirect("solicitacoes_acesso")

    pendentes = SolicitacaoAcesso.objects.filter(status=SolicitacaoAcesso.Status.PENDENTE)
    historico = SolicitacaoAcesso.objects.exclude(status=SolicitacaoAcesso.Status.PENDENTE)[:20]
    return render(
        request,
        "core/solicitacoes_acesso.html",
        {"pendentes": pendentes, "historico": historico},
    )


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
            motivo = request.POST.get("motivo", "").strip()
            if novo_status in (SessaoTratamento.Status.CANCELADA, SessaoTratamento.Status.FALTOU):
                sessao.motivo = motivo[:300]
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
    "auditoria": ("Usuários, Permissões e Auditoria", "Perfis, acessos e trilha de auditoria."),
}


@login_required
def modulo_planejado(request, slug):
    titulo, descricao = MODULOS.get(slug, ("Módulo planejado", "Funcionalidade em planejamento."))
    contexto = _contexto(request, titulo)
    contexto["descricao_modulo"] = descricao
    return render(request, "core/modulo_planejado.html", contexto)


@login_required
def importacoes(request):
    contexto = _contexto(request, "Importação de Planilhas")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return render(request, "core/importacoes.html", contexto)
    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )

    form = ImportacaoArquivoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and pode_editar:
        if "enviar_arquivo" in request.POST and form.is_valid():
            import tempfile

            arquivo = request.FILES["arquivo"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temporario:
                temporario.write(arquivo.read())
                caminho = temporario.name
            request.session["importacao_caminho"] = caminho
            request.session["importacao_nome"] = arquivo.name
            request.session["importacao_tipo"] = request.POST.get("importacao_tipo", "medicamentos")
            messages.success(request, "Arquivo recebido. Defina a aba e o mapeamento das colunas.")
            return redirect("importacao_preparar")

    historico = clinica.importacoes.select_related("usuario")[:20]
    transferencias_importadas = (
        clinica.transferencias_recebidas.filter(importada=True)
        .exclude(status=Transferencia.Status.CANCELADA)
        .select_related("clinica_origem", "criado_por")
        .prefetch_related("itens__apresentacao__medicamento")
    )
    for transferencia in transferencias_importadas:
        transferencia.total_itens = transferencia.itens.count()
        transferencia.quantidade_total = sum(
            item.quantidade for item in transferencia.itens.all()
        )
    contexto.update(
        form=form,
        historico=historico,
        pode_editar=pode_editar,
        transferencias_importadas=transferencias_importadas,
    )
    return render(request, "core/importacoes.html", contexto)


@login_required
def importacao_preparar(request):
    contexto = _contexto(request, "Preparar Importação")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return render(request, "core/importacoes.html", contexto)
    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )
    if not pode_editar:
        return HttpResponse("Perfil sem permissão para importar.", status=403)

    caminho = request.session.get("importacao_caminho")
    if not caminho or not os.path.exists(caminho):
        messages.error(request, "Nenhum arquivo em preparação. Envie novamente.")
        return redirect("importacoes")

    tipo = request.session.get("importacao_tipo", "medicamentos")

    if request.method == "POST" and "confirmar_importacao" in request.POST:
        nome_aba = request.POST.get("aba", "")
        if tipo == "medicamentos":
            campos = ["nome", "principio_ativo", "descricao", "concentracao", "quantidade_mg"]
        elif tipo == "gmed":
            campos = ["nome", "principio_ativo", "descricao", "concentracao", "quantidade_mg"]
        else:
            campos = [
                "numero", "data", "medicamento", "descricao",
                "quantidade", "lote", "validade",
            ]
        mapeamento = {}
        for campo in campos:
            indice = request.POST.get(f"map_{campo}", "")
            if indice:
                try:
                    mapeamento[campo] = int(indice)
                except ValueError:
                    continue
        if tipo in ("medicamentos", "gmed"):
            campos_obrigatorios = ["nome", "descricao", "quantidade_mg"]
        else:
            campos_obrigatorios = ["numero", "medicamento", "quantidade"]
        campos_faltando = [campo for campo in campos_obrigatorios if campo not in mapeamento]
        if campos_faltando:
            messages.error(
                request,
                f"Mapeie os campos obrigatórios: {', '.join(campos_faltando)}.",
            )
            return redirect("importacao_preparar")
        try:
            if tipo == "medicamentos":
                importadas, com_erro, erros, novas = importar_medicamentos(
                    clinica, caminho, nome_aba, mapeamento, usuario=request.user
                )
            elif tipo == "gmed":
                importadas, com_erro, erros, novas, duplicadas = importar_gmed(
                    clinica, caminho, nome_aba, mapeamento, usuario=request.user
                )
            else:
                origem = Clinica.objects.filter(nome__icontains="Ji-Paraná").first()
                if not origem or origem.pk == clinica.pk:
                    messages.error(
                        request,
                        "Cadastre a clínica Ji-Paraná (com esse nome) para importar transferências dela.",
                    )
                    return redirect("importacao_preparar")
                importadas, com_erro, erros, duplicadas = importar_transferencias(
                    clinica_destino=clinica,
                    clinica_origem=origem,
                    caminho_arquivo=caminho,
                    nome_aba=nome_aba,
                    mapeamento=mapeamento,
                    usuario=request.user,
                )
        except Exception as exc:
            messages.error(request, f"Não foi possível concluir a importação: {exc}.")
            return redirect("importacoes")
        registrar_auditoria(
            clinica,
            request.user,
            f"Importação ({tipo})",
            f"{importadas} linha(s) importada(s), {com_erro} com erro ({os.path.basename(caminho)}, aba '{nome_aba}').",
            request=request,
        )
        resultado = {"importadas": importadas, "com_erro": com_erro, "erros": erros[:50], "tipo": tipo}
        if tipo != "medicamentos":
            resultado["duplicadas"] = duplicadas
        messages.success(request, f"Importação concluída: {importadas} linha(s) importada(s), {com_erro} com erro.")
        contexto.update(resultado_importacao=resultado)
        return render(request, "core/importacao_preparar.html", contexto)

    try:
        abas = inspecionar_importacao(caminho)
    except Exception as exc:
        messages.error(request, f"Não foi possível ler o arquivo: {exc}.")
        return redirect("importacoes")

    contexto.update(abas=abas, nome_arquivo=request.session.get("importacao_nome", ""), tipo=tipo)
    return render(request, "core/importacao_preparar.html", contexto)


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
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return render(request, "core/alertas.html", contexto)

    pode_enviar_email = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )
    if request.method == "POST":
        if not pode_enviar_email:
            return HttpResponse("Perfil sem permissão para enviar alertas.", status=403)
        destinatarios, total_alertas = enviar_alertas_por_email(
            clinica, usuario=request.user, request=request
        )
        if total_alertas == 0:
            messages.info(request, "Nenhum alerta para notificar no momento.")
        elif destinatarios == 0:
            messages.warning(request, "Há alertas, mas nenhum destinatário cadastrado com email.")
        else:
            messages.success(
                request, f"Alertas enviados por email para {destinatarios} destinatário(s)."
            )
        return redirect("alertas")

    vencidos, criticos_validade, alertas_validade, estoque_baixo = coletar_alertas_estoque(clinica)

    contexto.update(
        vencidos=vencidos,
        criticos_validade=criticos_validade,
        alertas_validade=alertas_validade,
        estoque_baixo=estoque_baixo,
        total_alertas=len(vencidos) + len(criticos_validade) + len(estoque_baixo),
        pode_enviar_email=pode_enviar_email,
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
def sobras(request):
    """Sobras reais: registro manual de sobras físicas pós-manipulação e sua
    reutilização/descarte, com contagem de expiradas pendentes de ação.
    """
    contexto = _contexto(request, "Sobras Reais")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return render(request, "core/sobras.html", contexto)

    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )

    if request.method == "POST" and pode_editar:
        if "registrar_sobra" in request.POST:
            form = SobraRealForm(request.POST, clinica=clinica)
            if form.is_valid():
                form.save(usuario=request.user, clinica=clinica)
                messages.success(request, "Sobra registrada.")
                return redirect("sobras")
        else:
            sobra_id = request.POST.get("sobra_id")
            sobra = get_object_or_404(SobraReal, pk=sobra_id, clinica=clinica)
            if "reutilizar_sobra" in request.POST:
                paciente = get_object_or_404(Paciente, pk=request.POST.get("paciente_destino"))
                sobra.reutilizar(paciente, request.user)
                messages.success(request, "Sobra reutilizada.")
            elif "descartar_sobra" in request.POST:
                sobra.descartar(request.POST.get("motivo_descarte", ""), request.user)
                messages.success(request, "Sobra descartada.")
            return redirect("sobras")

    form = SobraRealForm(clinica=clinica)
    contexto.update(
        form=form,
        sobras_validas=sobras_reais_validas(clinica),
        sobras_expiradas=sobras_reais_expiradas(clinica),
        paciente_lista=clinica.pacientes.filter(ativo=True),
    )
    return render(request, "core/sobras.html", contexto)


@login_required
def transferencias(request):
    contexto = _contexto(request, "Transferências entre Unidades")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return render(request, "core/transferencias.html", contexto)

    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )

    if request.method == "POST" and pode_editar:
        if "criar_transferencia" in request.POST:
            destino_id = request.POST.get("clinica_destino")
            destino = Clinica.objects.filter(pk=destino_id, ativa=True).exclude(pk=clinica.pk).first()
            erros = []
            itens = []
            if not destino:
                erros.append("Selecione uma clínica de destino válida.")
            apresentacoes = Apresentacao.objects.filter(
                medicamento__clinica=clinica, ativa=True
            ).select_related("medicamento")
            for apresentacao in apresentacoes:
                chave = f"qtd_{apresentacao.pk}"
                valor = request.POST.get(chave, "").strip()
                if not valor:
                    continue
                try:
                    quantidade = int(valor)
                except ValueError:
                    continue
                if quantidade <= 0:
                    continue
                disponivel = calcular_estoque_disponivel_apresentacao(clinica, apresentacao)
                if quantidade > disponivel:
                    erros.append(
                        f"{apresentacao}: quantidade ({quantidade}) maior que o disponível ({disponivel})."
                    )
                    continue
                itens.append((apresentacao, quantidade))
            if erros:
                for erro in erros:
                    messages.error(request, erro)
                return redirect("transferencias")
            if not itens:
                messages.error(request, "Informe ao menos um item com quantidade válida.")
                return redirect("transferencias")
            with transaction.atomic():
                transferencia = Transferencia.objects.create(
                    clinica_origem=clinica,
                    clinica_destino=destino,
                    criado_por=request.user,
                    observacao=request.POST.get("observacao", ""),
                )
                transferencia.numero = transferencia.gerar_numero()
                transferencia.save(update_fields=["numero"])
                for apresentacao, quantidade in itens:
                    ItemTransferencia.objects.create(
                        transferencia=transferencia,
                        apresentacao=apresentacao,
                        quantidade=quantidade,
                    )
                registrar_auditoria(
                    clinica,
                    request.user,
                    "Criação de transferência",
                    f"Transferência {transferencia.numero} criada para {destino.nome} com {len(itens)} item(ns).",
                    request=request,
                )
            messages.success(request, f"Transferência {transferencia.numero} criada em rascunho.")
            return redirect("detalhe_transferencia", pk=transferencia.pk)

    transferencias = (
        clinica.transferencias_enviadas.select_related("clinica_destino", "criado_por")
        .prefetch_related("itens__apresentacao__medicamento")[:20]
    )
    recebidas = (
        clinica.transferencias_recebidas.select_related("clinica_origem")
        .prefetch_related("itens__apresentacao__medicamento")[:20]
    )
    clinicas_destino = Clinica.objects.filter(ativa=True).exclude(pk=clinica.pk).order_by("nome")
    apresentacoes = Apresentacao.objects.filter(
        medicamento__clinica=clinica, ativa=True
    ).select_related("medicamento")
    linhas_apresentacoes = []
    for apresentacao in apresentacoes:
        apresentacao.disponivel = calcular_estoque_disponivel_apresentacao(clinica, apresentacao)
        if apresentacao.disponivel > 0:
            linhas_apresentacoes.append(apresentacao)
    contexto.update(
        transferencias=transferencias,
        recebidas=recebidas,
        clinicas_destino=clinicas_destino,
        apresentacoes=linhas_apresentacoes,
        pode_editar=pode_editar,
    )
    return render(request, "core/transferencias.html", contexto)


@login_required
def detalhe_transferencia(request, pk):
    contexto = _contexto(request, "Detalhe da Transferência")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return HttpResponse("Clínica não encontrada.", status=404)

    transferencia = (
        Transferencia.objects.filter(pk=pk)
        .select_related("clinica_origem", "clinica_destino", "criado_por", "recebido_por")
        .first()
    )
    if not transferencia or clinica not in [
        transferencia.clinica_origem, transferencia.clinica_destino,
    ]:
        return HttpResponse("Transferência não encontrada.", status=404)

    pode_editar = _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    )

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "enviar" and pode_editar and transferencia.clinica_origem == clinica:
            if transferencia.status != Transferencia.Status.RASCUNHO:
                messages.error(request, "Somente rascunhos podem ser enviados.")
                return redirect("detalhe_transferencia", pk=transferencia.pk)
            falhas = []
            with transaction.atomic():
                for item in transferencia.itens.select_related("apresentacao"):
                    ok, _ = processar_saida_lotes(
                        clinica,
                        item.apresentacao,
                        item.quantidade,
                        usuario=request.user,
                        observacao=f"Transferência {transferencia.numero} para {transferencia.clinica_destino.nome}",
                    )
                    if not ok:
                        falhas.append(item.apresentacao)
                if falhas:
                    transaction.set_rollback(True)
                    for apresentacao in falhas:
                        messages.error(
                            request, f"Estoque insuficiente para {apresentacao}. Transferência não enviada."
                        )
                    return redirect("detalhe_transferencia", pk=transferencia.pk)
                transferencia.status = Transferencia.Status.EM_TRANSITO
                transferencia.save(update_fields=["status"])
                registrar_auditoria(
                    clinica,
                    request.user,
                    "Envio de transferência",
                    f"Transferência {transferencia.numero} enviada para {transferencia.clinica_destino.nome}.",
                    request=request,
                )
            messages.success(request, "Transferência enviada. Estoque baixado na origem.")
            return redirect("detalhe_transferencia", pk=transferencia.pk)

        if acao == "cancelar" and pode_editar and transferencia.clinica_origem == clinica:
            if transferencia.status not in [
                Transferencia.Status.RASCUNHO, Transferencia.Status.EM_TRANSITO,
            ]:
                messages.error(request, "Transferência não pode ser cancelada.")
                return redirect("detalhe_transferencia", pk=transferencia.pk)
            transferencia.status = Transferencia.Status.CANCELADA
            transferencia.save(update_fields=["status"])
            registrar_auditoria(
                clinica,
                request.user,
                "Cancelamento de transferência",
                f"Transferência {transferencia.numero} cancelada.",
                request=request,
            )
            messages.success(request, "Transferência cancelada.")
            return redirect("detalhe_transferencia", pk=transferencia.pk)

        if acao == "receber" and pode_editar and transferencia.clinica_destino == clinica:
            recebivel_importada = (
                transferencia.importada
                and transferencia.status == Transferencia.Status.RASCUNHO
            )
            if transferencia.status != Transferencia.Status.EM_TRANSITO and not recebivel_importada:
                messages.error(request, "Somente transferências em trânsito podem ser recebidas.")
                return redirect("detalhe_transferencia", pk=transferencia.pk)
            erros = []
            with transaction.atomic():
                for item in transferencia.itens.select_related("apresentacao"):
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
                        erros.append(f"{item.apresentacao}: informe lote e validade.")
                        continue
                    try:
                        data_validade = date.fromisoformat(validade)
                    except ValueError:
                        erros.append(f"{item.apresentacao}: validade inválida.")
                        continue
                    if qtd_recebida > item.restante:
                        erros.append(
                            f"{item.apresentacao}: recebido ({qtd_recebida}) maior que o pendente ({item.restante})."
                        )
                        continue
                    lote, criado = Lote.objects.get_or_create(
                        clinica=clinica,
                        apresentacao=item.apresentacao,
                        numero_lote=numero_lote,
                        defaults={
                            "data_validade": data_validade,
                            "quantidade_inicial": qtd_recebida,
                            "quantidade_atual": qtd_recebida,
                        },
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
                        observacao=f"Recebimento da transferência {transferencia.numero} (origem: {transferencia.clinica_origem.nome})",
                    )
                    item.quantidade_recebida += qtd_recebida
                    item.save(update_fields=["quantidade_recebida"])
                if erros:
                    transaction.set_rollback(True)
                    for erro in erros:
                        messages.error(request, erro)
                    return redirect("detalhe_transferencia", pk=transferencia.pk)
                if not transferencia.itens.filter(quantidade_recebida__lt=F("quantidade")).exists():
                    transferencia.status = Transferencia.Status.RECEBIDA
                    transferencia.recebido_por = request.user
                    transferencia.data_recebimento = timezone.now()
                    transferencia.save(update_fields=["status", "recebido_por", "data_recebimento"])
                registrar_auditoria(
                    clinica,
                    request.user,
                    "Recebimento de transferência",
                    f"Recebimento registrado para a transferência {transferencia.numero}.",
                    request=request,
                )
            messages.success(request, "Recebimento registrado. Lotes criados no estoque de destino.")
            return redirect("detalhe_transferencia", pk=transferencia.pk)

    itens = transferencia.itens.select_related("apresentacao__medicamento")
    contexto.update(
        transferencia=transferencia,
        itens=itens,
        pode_editar=pode_editar,
        e_origem=transferencia.clinica_origem == clinica,
        e_destino=transferencia.clinica_destino == clinica,
        recebivel_importada=(
            transferencia.importada
            and transferencia.status == Transferencia.Status.RASCUNHO
        ),
    )
    return render(request, "core/detalhe_transferencia.html", contexto)


@login_required
def relatorios(request):
    contexto = _contexto(request, "Relatórios e Indicadores Administrativos")
    clinica = contexto["clinica"]
    if clinica:
        agora = timezone.localtime()
        periodo_texto = request.GET.get("mes") or agora.strftime("%Y-%m")
        try:
            inicio_mes = date.fromisoformat(f"{periodo_texto}-01")
        except ValueError:
            inicio_mes = date(agora.year, agora.month, 1)
        ano, mes = inicio_mes.year, inicio_mes.month
        mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)
        proximo_mes = (inicio_mes.replace(day=28) + timedelta(days=7)).replace(day=1)

        lotes = clinica.lotes.filter(ativo=True)
        total_lotes = lotes.count()
        total_frascos_estoque = sum(l.quantidade_atual for l in lotes)
        pacientes_ativos = clinica.pacientes.filter(ativo=True).count()

        sessoes_mes = clinica.sessoes.filter(
            data_hora__year=ano, data_hora__month=mes
        )
        sessoes_por_status = {
            status: sessoes_mes.filter(status=status).count()
            for status, _ in SessaoTratamento.Status.choices
        }
        total_sessoes_mes = sessoes_mes.count()

        def taxa(contador):
            return round(contador * 100 / total_sessoes_mes, 1) if total_sessoes_mes else 0

        consumo_mes = (
            MovimentacaoEstoque.objects.filter(
                clinica=clinica,
                tipo=MovimentacaoEstoque.TipoMovimentacao.SAIDA,
                data_hora__year=ano,
                data_hora__month=mes,
            )
            .values("lote__apresentacao__medicamento__nome", "lote__apresentacao__descricao")
            .annotate(total_frascos=Sum("quantidade"))
            .order_by("total_frascos")[:10]
        )
        consumo_mes = [
            {
                "medicamento": item["lote__apresentacao__medicamento__nome"],
                "apresentacao": item["lote__apresentacao__descricao"],
                "frascos": abs(item["total_frascos"]),
            }
            for item in consumo_mes
        ]

        sobras_reutilizadas = clinica.sobras_reais.filter(
            data_reutilizacao__year=ano, data_reutilizacao__month=mes
        )
        sobras_descartadas = clinica.sobras_reais.filter(
            data_descarte__year=ano, data_descarte__month=mes
        )
        sobras_mes = list(
            sobras_reutilizadas.select_related("apresentacao__medicamento", "paciente_destino")
        ) + list(
            sobras_descartadas.select_related("apresentacao__medicamento", "paciente_destino")
        )
        sobras_mes.sort(
            key=lambda s: s.data_reutilizacao or s.data_descarte or s.criada_em, reverse=True
        )
        sobras_reutilizadas_mg = float(
            sobras_reutilizadas.aggregate(total=Sum("quantidade_mg"))["total"] or 0
        )
        sobras_descartadas_mg = float(
            sobras_descartadas.aggregate(total=Sum("quantidade_mg"))["total"] or 0
        )
        pedidos_mes = clinica.pedidos_compra.filter(criado_em__year=ano, criado_em__month=mes)
        transferencias_recebidas_mes = clinica.transferencias_recebidas.filter(
            data_recebimento__year=ano, data_recebimento__month=mes
        ).count()

        por_validade = {"vencido": 0, "critico": 0, "alerta": 0, "ok": 0}
        por_estoque = {"esgotado": 0, "baixo": 0, "ok": 0}
        lotes_urgentes = []
        for lote in lotes:
            validade, estoque = lote.status_validade, lote.status_estoque
            por_validade[validade] += 1
            por_estoque[estoque] += 1
            if validade in ("vencido", "critico") or estoque in ("esgotado", "baixo"):
                lotes_urgentes.append((lote, validade, estoque))
        lotes_urgentes.sort(
            key=lambda item: (
                item[1] != "vencido",
                item[1] != "critico",
                item[2] != "esgotado",
                item[0].dias_para_vencer,
            )
        )

        contexto.update(
            inicio_mes=inicio_mes,
            mes_anterior=mes_anterior,
            proximo_mes=proximo_mes,
            total_lotes=total_lotes,
            total_frascos_estoque=total_frascos_estoque,
            pacientes_ativos=pacientes_ativos,
            sessoes_realizadas_mes=sessoes_por_status["realizada"],
            total_sessoes_mes=total_sessoes_mes,
            sessoes_por_status=sessoes_por_status,
            taxa_faltas=taxa(sessoes_por_status["faltou"]),
            taxa_cancelamento=taxa(sessoes_por_status["cancelada"]),
            taxa_presenca=taxa(sessoes_por_status["realizada"]),
            consumo_mes=consumo_mes,
            sobras_reutilizadas_mg=sobras_reutilizadas_mg,
            sobras_reutilizadas_qtd=sobras_reutilizadas.count(),
            sobras_descartadas_mg=sobras_descartadas_mg,
            sobras_descartadas_qtd=sobras_descartadas.count(),
            sobras_mes=sobras_mes[:10],
            pedidos_criados_mes=pedidos_mes.count(),
            pedidos_recebidos_mes=pedidos_mes.filter(
                status=PedidoCompra.Status.RECEBIDO
            ).count(),
            transferencias_recebidas_mes=transferencias_recebidas_mes,
            por_validade=por_validade,
            por_estoque=por_estoque,
            lotes_urgentes=lotes_urgentes[:10],
        )
    return render(request, "core/relatorios.html", contexto)


@login_required
def relatorios_consumo_csv(request):
    perfil = _perfil(request)
    if not perfil:
        return HttpResponse("Usuário sem clínica vinculada.", status=403)
    agora = timezone.localtime()
    periodo_texto = request.GET.get("mes") or agora.strftime("%Y-%m")
    try:
        inicio_mes = date.fromisoformat(f"{periodo_texto}-01")
    except ValueError:
        inicio_mes = date(agora.year, agora.month, 1)
    consumos = (
        MovimentacaoEstoque.objects.filter(
            clinica=perfil.clinica,
            tipo=MovimentacaoEstoque.TipoMovimentacao.SAIDA,
            data_hora__year=inicio_mes.year,
            data_hora__month=inicio_mes.month,
        )
        .values("lote__apresentacao__medicamento__nome", "lote__apresentacao__descricao")
        .annotate(total_frascos=Sum("quantidade"))
        .order_by("total_frascos")
    )
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="consumo-oncologia-cacoal.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Mes", "Medicamento", "Apresentacao", "Frascos"])
    for item in consumos:
        writer.writerow(
            [
                inicio_mes.strftime("%Y-%m"),
                item["lote__apresentacao__medicamento__nome"],
                item["lote__apresentacao__descricao"],
                abs(item["total_frascos"]),
            ]
        )
    return response


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


@login_required
def importar_relatorio_conferencia(request):
    """Importa o PDF do relatório de transferência de Ji-Paraná (Fase 3)."""
    contexto = _contexto(request, "Importar Relatório de Transferência")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return HttpResponse("Clínica não encontrada.", status=404)
    if not _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    ):
        return HttpResponse("Sem permissão.", status=403)

    clinicas_origem = Clinica.objects.filter(ativa=True).exclude(pk=clinica.pk).order_by("nome")

    if request.method == "POST":
        arquivo = request.FILES.get("relatorio")
        origem_pk = request.POST.get("clinica_origem")
        if not arquivo or not origem_pk:
            messages.error(request, "Informe o arquivo PDF e a clínica de origem.")
            return redirect("importar_relatorio_conferencia")
        if not arquivo.name.lower().endswith(".pdf"):
            messages.error(request, "Somente arquivos PDF são aceitos.")
            return redirect("importar_relatorio_conferencia")
        origem = Clinica.objects.filter(pk=origem_pk).first()
        if origem is None:
            messages.error(request, "Clínica de origem inválida.")
            return redirect("importar_relatorio_conferencia")
        transferencia, reconhecidos, erros = importar_transferencia_pdf(
            origem, clinica, arquivo, usuario=request.user
        )
        for erro in erros:
            messages.warning(request, erro)
        if transferencia is None:
            messages.error(request, "Relatório não importado.")
            return redirect("importar_relatorio_conferencia")
        messages.success(
            request,
            f"Relatório importado: transferência {transferencia.numero} com "
            f"{len(reconhecidos)} item(ns). Confira as pendências.",
        )
        return redirect("conferencia_transferencia", pk=transferencia.pk)

    contexto.update(clinicas_origem=clinicas_origem)
    return render(request, "core/importar_relatorio_conferencia.html", contexto)


@login_required
def conferencia_transferencia(request, pk):
    """Tela de conferência automatizada: evidências → extração → reconciliação.

    Aceita upload de fotos (com ou sem dados manuais), resolução de
    divergências e mostra o estado atual da conferência.
    """
    contexto = _contexto(request, "Conferência de Transferência")
    clinica, perfil = contexto["clinica"], contexto["perfil"]
    if not clinica:
        return HttpResponse("Clínica não encontrada.", status=404)
    if not _pode_editar(
        perfil, {PerfilUsuario.Papel.ADMINISTRADOR, PerfilUsuario.Papel.FARMACEUTICO}
    ):
        return HttpResponse("Sem permissão.", status=403)

    transferencia = (
        Transferencia.objects.filter(pk=pk, clinica_destino=clinica)
        .select_related("clinica_origem", "clinica_destino", "criado_por")
        .first()
    )
    if transferencia is None:
        return HttpResponse("Transferência não encontrada.", status=404)

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "adicionar_evidencia":
            arquivo = request.FILES.get("foto")
            item_pk = request.POST.get("item")
            if not arquivo or not item_pk:
                messages.error(request, "Envie a foto e selecione o item.")
                return redirect("conferencia_transferencia", pk=pk)
            item = transferencia.itens.filter(pk=item_pk).first()
            if item is None:
                messages.error(request, "Item de transferência inválido.")
                return redirect("conferencia_transferencia", pk=pk)
            dados = {}
            validade_raw = request.POST.get("validade", "").strip()
            validade = None
            if validade_raw:
                try:
                    validade = date.fromisoformat(validade_raw)
                except ValueError:
                    messages.error(request, "Validade deve estar em formato YYYY-MM-DD.")
                    return redirect("conferencia_transferencia", pk=pk)
            dados.update(
                {
                    "nome_produto": request.POST.get("nome_produto", "").strip()
                    or str(item.apresentacao),
                    "lote": request.POST.get("lote", "").strip(),
                    "validade": validade,
                    "quantidade": request.POST.get("quantidade", "").strip(),
                    "confianca_produto": 1.0,
                }
            )
            try:
                _, extracao = processar_evidencia(
                    transferencia,
                    arquivo,
                    usuario=request.user,
                    item=item,
                    dados=dados,
                )
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect("conferencia_transferencia", pk=pk)
            observado = {
                "produto_observado": item.apresentacao,
                "lote": extracao.lote,
                "validade": extracao.validade,
                "quantidade": extracao.quantidade,
                "foto_insuficiente": extracao.requer_revisao,
                "confianca_final": _confianca_consolidada(extracao),
            }
            reconciliar_item(item, observado, usuario=request.user)
            derivar_status_conferencia(transferencia, usuario=request.user)
            if extracao.requer_revisao:
                messages.warning(request, "Evidência exige revisão manual (campos ausentes).")
            else:
                messages.success(request, "Evidência processada e reconciliada.")
            return redirect("conferencia_transferencia", pk=pk)

        if acao == "resolver_divergencia":
            from .reconciliacao import resolver_divergencia

            divergencia = transferencia.divergencias.filter(
                pk=request.POST.get("divergencia"),
                status=DivergenciaTransferencia.StatusResolucao.PENDENTE,
            ).first()
            if divergencia is None:
                messages.error(request, "Divergência não encontrada.")
            else:
                resolver_divergencia(
                    divergencia, request.user, request.POST.get("resolucao", "").strip()
                )
                derivar_status_conferencia(transferencia, usuario=request.user)
                messages.success(request, "Divergência resolvida.")
            return redirect("conferencia_transferencia", pk=pk)

        if acao == "aprovar":
            if (
                transferencia.status_conferencia
                != Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO
            ):
                messages.error(request, "Transferência não está pronta para aprovação.")
                return redirect("conferencia_transferencia", pk=pk)
            transicionar(
                transferencia,
                Transferencia.StatusConferencia.APROVADA,
                usuario=request.user,
                motivo="Aprovação da conferência pelo farmacêutico responsável.",
            )
            sincronizar_status_operacional(transferencia)
            messages.success(request, "Conferência aprovada.")
            return redirect("conferencia_transferencia", pk=pk)

        if acao == "integrar_estoque":
            if transferencia.status_conferencia != Transferencia.StatusConferencia.APROVADA:
                messages.error(request, "Somente conferências aprovadas integram o estoque.")
                return redirect("conferencia_transferencia", pk=pk)
            with transaction.atomic():
                try:
                    entradas = integrar_ao_estoque(transferencia, request.user)
                except ValueError as exc:
                    messages.error(request, str(exc))
                    return redirect("conferencia_transferencia", pk=pk)
                transicionar(
                    transferencia,
                    Transferencia.StatusConferencia.INTEGRADA_AO_ESTOQUE,
                    usuario=request.user,
                    motivo=f"{len(entradas)} lote(s) criados no estoque de destino.",
                )
                sincronizar_status_operacional(transferencia)
            registrar_auditoria(
                clinica,
                request.user,
                "Integração ao estoque (conferência automatizada)",
                f"Transferência {transferencia.numero}: {len(entradas)} lotes de entrada.",
                request=request,
            )
            messages.success(request, "Transferência integrada ao estoque.")
            return redirect("detalhe_transferencia", pk=pk)

    itens = transferencia.itens.select_related(
        "apresentacao__medicamento", "reconciliacao"
    )
    evidencias = transferencia.evidencias.select_related("item").prefetch_related(
        "extracoes"
    )
    divergencias = transferencia.divergencias.select_related("item", "resolvida_por").order_by(
        "-criada_em"
    )
    contexto.update(
        transferencia=transferencia,
        itens=itens,
        evidencias=evidencias,
        divergencias=divergencias,
        pode_aprovar=(
            transferencia.status_conferencia
            == Transferencia.StatusConferencia.PRONTA_PARA_APROVACAO
        ),
        pode_integrar=(
            transferencia.status_conferencia == Transferencia.StatusConferencia.APROVADA
        ),
    )
    return render(request, "core/conferencia_transferencia.html", contexto)


def _confianca_consolidada(extracao):
    """Confiança final consolidada da extração (média simples dos campos)."""
    valores = [
        extracao.confianca_produto,
        extracao.confianca_lote,
        extracao.confianca_validade,
        extracao.confianca_quantidade,
    ]
    presentes = [float(v) for v in valores if v is not None]
    if not presentes:
        return None
    return round(sum(presentes) / len(presentes), 2)


