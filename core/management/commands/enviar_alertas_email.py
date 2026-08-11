"""Envia alertas de estoque e faltas por email para as clínicas com notificações pendentes.

Uso (agende diariamente no cron/scheduler do servidor):
    python manage.py enviar_alertas_email
"""

from django.core.management.base import BaseCommand

from core.models import Clinica
from core.services import enviar_alertas_por_email


class Command(BaseCommand):
    help = "Envia por email os alertas de estoque, validade e faltas de todas as clínicas."

    def handle(self, *args, **options):
        total_clinicas, total_destinatarios, total_alertas = 0, 0, 0
        for clinica in Clinica.objects.filter(ativa=True):
            destinatarios, alertas = enviar_alertas_por_email(clinica)
            if destinatarios or alertas:
                total_clinicas += 1
                total_destinatarios += destinatarios
                total_alertas += alertas
                self.stdout.write(
                    f"{clinica.nome}: {alertas} alerta(s) para {destinatarios} destinatário(s)."
                )
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído: {total_clinicas} clínica(s) notificada(s), "
                f"{total_alertas} alerta(s), {total_destinatarios} envio(s)."
            )
        )
