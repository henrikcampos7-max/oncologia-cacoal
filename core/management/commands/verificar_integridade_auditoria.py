"""Verifica a integridade da cadeia de hashes do log de auditoria.

Uso:
    python manage.py verificar_integridade_auditoria
    python manage.py verificar_integridade_auditoria --clinica 1
"""

from django.core.management.base import BaseCommand

from core.models import Clinica, RegistroAuditoria


class Command(BaseCommand):
    help = (
        "Valida a cadeia SHA-256 do log de auditoria (append-only) por clínica "
        "e reporta registros divergentes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clinica",
            type=int,
            default=None,
            help="ID da clínica; sem o parâmetro, valida todas as ativas.",
        )

    def handle(self, *args, **options):
        clinicas = Clinica.objects.filter(ativa=True)
        if options["clinica"]:
            clinicas = Clinica.objects.filter(pk=options["clinica"])
        total_quebrados = 0
        for clinica in clinicas:
            valida, quebrados = RegistroAuditoria.verificar_integridade(clinica)
            if valida:
                self.stdout.write(
                    self.style.SUCCESS(f"{clinica.nome}: cadeia válida.")
                )
            else:
                total_quebrados += len(quebrados)
                self.stdout.write(
                    self.style.ERROR(
                        f"{clinica.nome}: {len(quebrados)} registro(s) divergente(s)."
                    )
                )
                for registro in quebrados:
                    self.stdout.write(
                        f"  pk={registro.pk} {registro.data_hora:%Y-%m-%d %H:%M} "
                        f"acao={registro.acao} hash={registro.hash_registro[:16]}..."
                    )
        if total_quebrados:
            self.stdout.write(
                self.style.ERROR(
                    f"Integridade comprometida: {total_quebrados} registro(s) "
                    "não conferem com a cadeia. Acione o administrador."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("Integridade OK em todas as clínicas verificadas.")
            )
