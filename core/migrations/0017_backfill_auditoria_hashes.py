"""Backfill: calcula a cadeia de hashes para registros de auditoria existentes."""

from django.db import migrations


def _backfill_hashes(apps, schema_editor):
    RegistroAuditoria = apps.get_model("core", "RegistroAuditoria")

    clinicas = sorted(
        set(
            RegistroAuditoria.objects.order_by("clinica_id")
            .values_list("clinica_id", flat=True)
        )
    )
    for clinica_id in clinicas:
        registros = list(
            RegistroAuditoria.objects.filter(clinica_id=clinica_id).order_by(
                "data_hora", "pk"
            )
        )
        hash_anterior = ""
        for registro in registros:
            payload = "|".join(
                str(v) if v is not None else ""
                for v in (
                    hash_anterior,
                    clinica_id,
                    registro.usuario_id if registro.usuario_id else "",
                    registro.acao,
                    registro.detalhes,
                    registro.ip_origem,
                    registro.data_hora.isoformat(),
                )
            )
            import hashlib

            registro.hash_registro = hashlib.sha256(
                payload.encode("utf-8")
            ).hexdigest()
            registro.hash_anterior = hash_anterior
            registro.save(update_fields=["hash_registro", "hash_anterior"])
            hash_anterior = registro.hash_registro


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_registroauditoria_hash_anterior_and_more"),
    ]

    operations = [
        migrations.RunPython(_backfill_hashes, migrations.RunPython.noop),
    ]