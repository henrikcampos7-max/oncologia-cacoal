from django.contrib import admin

from .models import (
    Apresentacao,
    Clinica,
    ItemProtocolo,
    Medicamento,
    Paciente,
    PerfilUsuario,
    Protocolo,
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


admin.site.site_header = "Oncologia Cacoal — Administração"
admin.site.site_title = "Oncologia Cacoal"
admin.site.index_title = "Cadastros e configurações"
