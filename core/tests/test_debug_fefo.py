from datetime import datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.models import (
    Clinica,
    ItemProtocolo,
    Medicamento,
    Paciente,
    Protocolo,
    SessaoTratamento,
)
from core.services import calcular_previsao_sobras


class DebugFefoTests(TestCase):
    def test_debug(self):
        clinica = Clinica.objects.create(nome="C")
        med = Medicamento.objects.create(clinica=clinica, nome="X", principio_ativo="A")
        ap = med.apresentacoes.create(
            concentracao="1",
            descricao="Frasco 500 mg",
            quantidade_mg=Decimal("500"),
            estabilidade_apos_abertura=Decimal("24"),
        )

        def adm(nome, dose, dia, hora):
            paciente = Paciente.objects.create(
                clinica=clinica, nome=nome, data_inicio=timezone.localdate()
            )
            proto = Protocolo.objects.create(clinica=clinica, nome=f"P {nome}")
            ItemProtocolo.objects.create(
                protocolo=proto, apresentacao=ap, dose_valor=Decimal(str(dose)), tipo_dose="fixa"
            )
            base = timezone.localdate() + timedelta(days=dia)
            SessaoTratamento.objects.create(
                clinica=clinica,
                paciente=paciente,
                protocolo=proto,
                data_hora=timezone.make_aware(
                    datetime.combine(base, datetime.min.time().replace(hour=hora))
                ),
                ciclo=1,
                dia_ciclo=1,
            )

        adm("Paciente A", 350, 0, 8)
        adm("Paciente B", 300, 0, 20)
        adm("Paciente C", 200, 1, 7)

        resultado = calcular_previsao_sobras(clinica)
        linha = resultado["apresentacoes"][0]
        for evento in linha["eventos"]:
            print(evento["tipo"], evento["paciente"], evento["mg"], evento["detalhe"], evento["data_hora"])
