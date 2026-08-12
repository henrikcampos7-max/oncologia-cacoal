from django.contrib import admin

from .models import (
    AliasMedicamento,
    Apresentacao,
    Clinica,
    DivergenciaTransferencia,
    ExtracaoEvidencia,
    ImportacaoArquivo,
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
    ReconciliacaoItemTransferencia,
    RegistroAuditoria,
    SessaoTratamento,
    SobraReal,
    SolicitacaoAcesso,
    Transferencia,
    TransferenciaEvidencia,
)


@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativa", "criada_em")
    list_filter = ("ativa",)
    search_fields = ("nome",)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "clinica", "papel", "ativo")
    list_filter = ("clinica", "papel", "ativo")
    search_fields = ("usuario__username", "usuario__email")


class ApresentacaoInline(admin.TabularInline):
    model = Apresentacao
    extra = 0


@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "clinica", "principio_ativo", "ativo")
    list_filter = ("clinica", "ativo")
    search_fields = ("nome", "principio_ativo")
    inlines = (ApresentacaoInline,)


class ItemProtocoloInline(admin.TabularInline):
    model = ItemProtocolo
    extra = 0


@admin.register(Protocolo)
class ProtocoloAdmin(admin.ModelAdmin):
    list_display = ("nome", "clinica", "intervalo_dias", "total_ciclos", "ativo")
    list_filter = ("clinica", "ativo")
    search_fields = ("nome", "diagnostico_referencia")
    inlines = (ItemProtocoloInline,)


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "clinica", "protocolo", "data_inicio", "ativo")
    list_filter = ("clinica", "ativo")
    search_fields = ("nome", "diagnostico")


@admin.register(SessaoTratamento)
class SessaoTratamentoAdmin(admin.ModelAdmin):
    list_display = ("data_hora", "paciente", "protocolo", "ciclo", "dia_ciclo", "status")
    list_filter = ("clinica", "status")
    search_fields = ("paciente__nome", "protocolo__nome")


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ("apresentacao", "numero_lote", "data_validade", "quantidade_atual", "estoque_minimo", "ativo")
    list_filter = ("clinica", "ativo")
    search_fields = ("numero_lote", "apresentacao__medicamento__nome")


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ("lote", "tipo", "quantidade", "usuario", "data_hora")
    list_filter = ("clinica", "tipo")
    search_fields = ("lote__numero_lote", "lote__apresentacao__medicamento__nome")


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Trilha de auditoria somente leitura (append-only, cadeia de hashes)."""

    list_display = ("data_hora", "usuario", "acao", "clinica", "hash_registro")
    list_filter = ("clinica", "acao")
    search_fields = ("usuario__username", "acao", "detalhes")
    readonly_fields = (
        "clinica",
        "usuario",
        "acao",
        "detalhes",
        "ip_origem",
        "data_hora",
        "hash_anterior",
        "hash_registro",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ItemPedidoCompraInline(admin.TabularInline):
    model = ItemPedidoCompra
    extra = 0


@admin.register(PedidoCompra)
class PedidoCompraAdmin(admin.ModelAdmin):
    list_display = ("numero", "clinica", "status", "solicitante", "criado_em")
    list_filter = ("clinica", "status")
    search_fields = ("numero", "fornecedor")
    inlines = (ItemPedidoCompraInline,)


class ItemTransferenciaInline(admin.TabularInline):
    model = ItemTransferencia
    extra = 0


@admin.register(Transferencia)
class TransferenciaAdmin(admin.ModelAdmin):
    list_display = ("numero", "clinica_origem", "clinica_destino", "status", "criado_em")
    list_filter = ("clinica_origem", "clinica_destino", "status")
    search_fields = ("numero",)
    inlines = (ItemTransferenciaInline,)


@admin.register(SolicitacaoAcesso)
class SolicitacaoAcessoAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "email", "clinica", "papel_solicitado", "status", "data_hora")
    list_filter = ("status", "clinica", "papel_solicitado")
    search_fields = ("nome_completo", "email")


@admin.register(ImportacaoArquivo)
class ImportacaoArquivoAdmin(admin.ModelAdmin):
    list_display = ("nome_arquivo", "clinica", "aba", "importadas", "com_erro", "data_hora")
    list_filter = ("clinica",)
    search_fields = ("nome_arquivo", "aba")


@admin.register(SobraReal)
class SobraRealAdmin(admin.ModelAdmin):
    list_display = (
        "apresentacao",
        "quantidade_mg",
        "status",
        "paciente_origem",
        "paciente_destino",
        "limite_estabilidade",
        "criada_em",
    )
    list_filter = ("clinica", "status")
    search_fields = ("apresentacao__medicamento__nome", "lote__codigo")
    readonly_fields = ("status", "data_reutilizacao", "data_descarte", "criada_por", "criada_em")


@admin.register(AliasMedicamento)
class AliasMedicamentoAdmin(admin.ModelAdmin):
    list_display = ("alias", "medicamento", "clinica")
    list_filter = ("clinica",)
    search_fields = ("alias", "medicamento__nome")


class ExtracaoEvidenciaInline(admin.StackedInline):
    model = ExtracaoEvidencia
    extra = 0
    readonly_fields = ("criado_em",)


@admin.register(TransferenciaEvidencia)
class TransferenciaEvidenciaAdmin(admin.ModelAdmin):
    list_display = ("pk", "transferencia", "item", "status", "suspeita_duplicidade", "criado_em")
    list_filter = ("status", "suspeita_duplicidade")
    search_fields = ("transferencia__numero", "hash_arquivo")
    inlines = (ExtracaoEvidenciaInline,)


@admin.register(ReconciliacaoItemTransferencia)
class ReconciliacaoItemTransferenciaAdmin(admin.ModelAdmin):
    list_display = (
        "item",
        "status_final",
        "match_produto",
        "match_lote",
        "match_quantidade",
        "status_validade",
        "confianca_final",
    )
    list_filter = ("status_final", "status_validade")


@admin.register(DivergenciaTransferencia)
class DivergenciaTransferenciaAdmin(admin.ModelAdmin):
    list_display = ("transferencia", "tipo", "severidade", "status", "criada_em")
    list_filter = ("tipo", "severidade", "status")
    search_fields = ("transferencia__numero",)


admin.site.site_header = "Oncologia Cacoal — Administração"
admin.site.site_title = "Oncologia Cacoal"
admin.site.index_title = "Cadastros e configurações"
