import os
from datetime import datetime, time
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import (
    Apresentacao,
    Clinica,
    ConfiguracaoClinica,
    ItemProtocolo,
    Lote,
    MedicacaoOral,
    Medicamento,
    MovimentacaoEstoque,
    Paciente,
    PerfilUsuario,
    Protocolo,
    SessaoTratamento,
)


class Command(BaseCommand):
    help = "Cria uma demonstração local idempotente usando exclusivamente dados fictícios."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirmar-dados-ficticios",
            action="store_true",
            help="Confirma que a carga será usada somente no ambiente local de demonstração.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("A carga demonstrativa é bloqueada quando DEBUG está desativado.")
        if not options["confirmar_dados_ficticios"]:
            raise CommandError("Use --confirmar-dados-ficticios para executar a carga local.")

        demo_password = os.getenv("ONCOLOGIA_DEMO_PASSWORD", "")
        if len(demo_password) < 15:
            raise CommandError("Defina ONCOLOGIA_DEMO_PASSWORD com pelo menos 15 caracteres.")

        clinic, _ = Clinica.objects.update_or_create(
            nome="Clínica Fictícia de Demonstração",
            defaults={"ativa": True},
        )

        user_model = get_user_model()
        user, _ = user_model.objects.update_or_create(
            username="demo.oncologia",
            defaults={
                "email": "demo@oncologia-cacoal.example",
                "first_name": "Usuário",
                "last_name": "Fictício",
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.set_password(demo_password)
        user.save(update_fields=["password"])
        PerfilUsuario.objects.update_or_create(
            usuario=user,
            defaults={
                "clinica": clinic,
                "papel": PerfilUsuario.Papel.ADMINISTRADOR,
                "ativo": True,
            },
        )
        ConfiguracaoClinica.objects.update_or_create(
            clinica=clinic,
            defaults={
                "setor": "Centro de Oncologia Fictício",
                "periodo_padrao_dias": ConfiguracaoClinica.PeriodoPainel.SETE_DIAS,
                "densidade_tabela": ConfiguracaoClinica.DensidadeTabela.PADRAO,
                "atualizado_por": user,
            },
        )

        medication, _ = Medicamento.objects.update_or_create(
            clinica=clinic,
            nome="Medicamento Fictício Alfa",
            defaults={
                "principio_ativo": "Substância fictícia sem uso clínico",
                "ativo": True,
            },
        )
        presentation, _ = Apresentacao.objects.update_or_create(
            medicamento=medication,
            descricao="Frasco demonstrativo 50 mg",
            defaults={
                "concentracao": "1 mg/mL (fictício)",
                "quantidade_mg": Decimal("50"),
                "ativa": True,
            },
        )

        today = timezone.localdate()

        lote_demo, _ = Lote.objects.update_or_create(
            clinica=clinic,
            apresentacao=presentation,
            numero_lote="LOT-2026-DEMO",
            defaults={
                "data_validade": today + timezone.timedelta(days=120),
                "quantidade_inicial": 100,
                "quantidade_atual": 85,
                "estoque_minimo": 10,
                "ativo": True,
            },
        )

        MovimentacaoEstoque.objects.get_or_create(
            clinica=clinic,
            lote=lote_demo,
            tipo=MovimentacaoEstoque.TipoMovimentacao.ENTRADA,
            quantidade=100,
            defaults={
                "usuario": user,
                "observacao": "Recebimento inicial fictício de demonstração",
            },
        )

        protocol, _ = Protocolo.objects.update_or_create(
            clinica=clinic,
            nome="PROTOCOLO FICTÍCIO DEMO — SEM USO CLÍNICO",
            defaults={
                "diagnostico_referencia": "Cenário inteiramente fictício",
                "intervalo_dias": 21,
                "total_ciclos": 1,
                "ativo": True,
            },
        )
        ItemProtocolo.objects.update_or_create(
            protocolo=protocol,
            apresentacao=presentation,
            defaults={
                "ciclos": "1",
                "dias_ciclo": "1",
                "tipo_dose": ItemProtocolo.TipoDose.FIXA,
                "dose_valor": Decimal("0"),
            },
        )

        today = timezone.localdate()
        patient, _ = Paciente.objects.update_or_create(
            clinica=clinic,
            nome="Paciente Fictícia Aurora",
            defaults={
                "diagnostico": "Diagnóstico fictício para demonstração",
                "protocolo": protocol,
                "data_inicio": today,
                "peso_kg": None,
                "altura_cm": None,
                "sexo": "",
                "ativo": True,
            },
        )
        appointment_time = timezone.make_aware(datetime.combine(today, time(hour=9)))
        SessaoTratamento.objects.update_or_create(
            clinica=clinic,
            paciente=patient,
            data_hora=appointment_time,
            ciclo=1,
            dia_ciclo=1,
            defaults={
                "protocolo": protocol,
                "status": SessaoTratamento.Status.AGENDADA,
                "observacoes": "Registro fictício para verificação visual local.",
            },
        )
        MedicacaoOral.objects.update_or_create(
            clinica=clinic,
            paciente=patient,
            medicamento=medication,
            data_inicio=today,
            defaults={
                "classe": MedicacaoOral.Classe.OUTROS,
                "quantidade_ciclos": 3,
                "intervalo_dias": 30,
                "status": MedicacaoOral.Status.PREVISTA,
                "observacoes": "Planejamento oral inteiramente fictício.",
            },
        )

        self.stdout.write(self.style.SUCCESS("Dados fictícios locais preparados com sucesso."))
        self.stdout.write("Usuário de demonstração: demo.oncologia")
        self.stdout.write("A senha permanece protegida pelo Windows e não é exibida.")
