from decimal import Decimal

from django.test import SimpleTestCase

from core.services import (
    calcular_dose_mg,
    calcular_frascos,
    calcular_superficie_corporal,
    numero_na_lista,
)


class CalculosAdministrativosTests(SimpleTestCase):
    def test_superficie_corporal_por_mosteller(self):
        self.assertEqual(calcular_superficie_corporal("70", "170"), Decimal("1.82"))

    def test_dose_por_superficie_exige_peso_e_altura(self):
        self.assertEqual(
            calcular_dose_mg("100", "mg_m2", "70", "170"), Decimal("182.00")
        )
        self.assertIsNone(calcular_dose_mg("100", "mg_m2", None, "170"))

    def test_dose_fixa_e_por_peso(self):
        self.assertEqual(calcular_dose_mg("75", "fixa"), Decimal("75"))
        self.assertEqual(calcular_dose_mg("2", "mg_kg", "70"), Decimal("140"))

    def test_frascos_sao_arredondados_para_cima(self):
        self.assertEqual(calcular_frascos("182", "50"), 4)
        self.assertEqual(calcular_frascos("0", "50"), 0)

    def test_ciclo_e_dia_precisam_estar_explicitamente_na_lista(self):
        self.assertTrue(numero_na_lista("1, 2, 4", 2))
        self.assertFalse(numero_na_lista("1, 2, 4", 3))
        self.assertFalse(numero_na_lista("1, inválido", 1))
