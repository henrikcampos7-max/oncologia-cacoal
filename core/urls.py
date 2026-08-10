from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import EmailOuUsuarioAuthenticationForm


urlpatterns = [
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
    path("", views.dashboard, name="dashboard"),
    path("agenda/", views.agenda, name="agenda"),
    path("agenda/exportar.csv", views.agenda_csv, name="agenda_csv"),
    path("agenda/imprimir/", views.agenda_impressao, name="agenda_impressao"),
    path("agenda/<int:pk>/status/", views.atualizar_status_sessao, name="atualizar_status_sessao"),
    path("pacientes/", views.pacientes, name="pacientes"),
    path("pacientes/<int:pk>/editar/", views.editar_paciente, name="editar_paciente"),
    path("medicamentos/", views.medicamentos, name="medicamentos"),
    path("medicamentos/<int:pk>/editar/", views.editar_medicamento, name="editar_medicamento"),
    path("apresentacoes/<int:pk>/editar/", views.editar_apresentacao, name="editar_apresentacao"),
    path("quantitativo/", views.quantitativo, name="quantitativo"),
    path("estoque/", views.estoque, name="estoque"),
    path("alertas/", views.alertas, name="alertas"),
    path("compras/", views.compras, name="compras"),
    path("relatorios/", views.relatorios, name="relatorios"),
    path("auditoria/", views.auditoria, name="auditoria"),
    path("modulos/<slug:slug>/", views.modulo_planejado, name="modulo_planejado"),
]
