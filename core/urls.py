from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import EmailOuUsuarioAuthenticationForm


urlpatterns = [
    path("favicon.ico", views.favicon, name="favicon"),
    path("saude/", views.health, name="health"),
    path(
        "entrar/",
        auth_views.LoginView.as_view(
            template_name="core/login.html",
            authentication_form=EmailOuUsuarioAuthenticationForm,
        ),
        name="login",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("solicitar-acesso/", views.solicitar_acesso, name="solicitar_acesso"),
    path("solicitacoes-acesso/", views.solicitacoes_acesso, name="solicitacoes_acesso"),
    path("", views.dashboard, name="dashboard"),
    path("agenda/", views.agenda, name="agenda"),
    path("agenda/exportar.csv", views.agenda_csv, name="agenda_csv"),
    path("agenda/imprimir/", views.agenda_impressao, name="agenda_impressao"),
    path("agenda/<int:pk>/editar/", views.editar_sessao, name="editar_sessao"),
    path("agenda/<int:pk>/status/", views.atualizar_status_sessao, name="atualizar_status_sessao"),
    path("pacientes/", views.pacientes, name="pacientes"),
    path("pacientes/<int:pk>/editar/", views.editar_paciente, name="editar_paciente"),
    path("medicacoes-orais/", views.medicacoes_orais, name="medicacoes_orais"),
    path(
        "medicacoes-orais/<int:pk>/editar/",
        views.editar_medicacao_oral,
        name="editar_medicacao_oral",
    ),
    path("medicamentos/", views.medicamentos, name="medicamentos"),
    path("medicamentos/<int:pk>/editar/", views.editar_medicamento, name="editar_medicamento"),
    path("apresentacoes/<int:pk>/editar/", views.editar_apresentacao, name="editar_apresentacao"),
    path("protocolos/", views.protocolos, name="protocolos"),
    path("protocolos/<int:pk>/editar/", views.editar_protocolo, name="editar_protocolo"),
    path("protocolos/itens/<int:pk>/remover/", views.remover_item_protocolo, name="remover_item_protocolo"),
    path("quantitativo/", views.quantitativo, name="quantitativo"),
    path("quantitativo/exportar.csv", views.quantitativo_csv, name="quantitativo_csv"),
    path("estoque/", views.estoque, name="estoque"),
    path("estoque/lotes/<int:pk>/editar/", views.editar_lote, name="editar_lote"),
    path("alertas/", views.alertas, name="alertas"),
    path("compras/", views.compras, name="compras"),
    path("compras/pedidos/<int:pk>/", views.detalhe_pedido, name="detalhe_pedido"),
    path("sobras/", views.sobras, name="sobras"),
path("transferencias/", views.transferencias, name="transferencias"),
    path("transferencias/<int:pk>/", views.detalhe_transferencia, name="detalhe_transferencia"),
    path(
        "transferencias/relatorio/importar/",
        views.importar_relatorio_conferencia,
        name="importar_relatorio_conferencia",
    ),
    path(
        "transferencias/<int:pk>/conferencia/",
        views.conferencia_transferencia,
        name="conferencia_transferencia",
    ),
    path("importacoes/", views.importacoes, name="importacoes"),
    path("importacoes/preparar/", views.importacao_preparar, name="importacao_preparar"),
    path("relatorios/", views.relatorios, name="relatorios"),
    path("relatorios/consumo.csv", views.relatorios_consumo_csv, name="relatorios_consumo_csv"),
    path(
        "relatorios/operacional.csv",
        views.relatorio_operacional_csv,
        name="relatorio_operacional_csv",
    ),
    path("relatorios/resumo.xlsx", views.exportar_resumo_excel, name="exportar_resumo_excel"),
    path("relatorios/imprimir/", views.relatorios_impressao, name="relatorios_impressao"),
    path("auditoria/", views.auditoria, name="auditoria"),
    path("auditoria/exportar.csv", views.auditoria_csv, name="auditoria_csv"),
    path("configuracoes/", views.configuracoes, name="configuracoes"),
    path("configuracoes/backup.json", views.backup_seguro, name="backup_seguro"),
    path("modulos/<slug:slug>/", views.modulo_planejado, name="modulo_planejado"),
]
