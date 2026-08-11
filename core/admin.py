from django.contrib import admin

from .models import (
    Apresentacao,
    Clinica,
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
    list_display = ("data_hora", "usuario", "acao", "clinica")
    list_filter = ("clinica", "acao")
    search_fields = ("usuario__username", "acao", "detalhes")


class ItemPedidoCompraInline(admin.TabularInline):
    model = ItemPedidoCompra
    extra = 0


@admin.register(PedidoCompra)
class PedidoCompraAdmin(admin.ModelAdmin):
    list_display = ("numero", "clinica", "status", "solicitante", "criado_em")
    list_filter = ("clinica", "status")
    search_fields = ("numero", "fornecedor")
    inlines = (ItemPedidoCompraInline,)


admin.site.site_header = "Oncologia Cacoal — Administração"
admin.site.site_title = "Oncologia Cacoal"
admin.site.index_title = "Cadastros e configurações"
