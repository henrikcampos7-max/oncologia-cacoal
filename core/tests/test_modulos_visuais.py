from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import (
    Clinica,
    ConfiguracaoClinica,
    MedicacaoOral,
    Medicamento,
    Paciente,
    PerfilUsuario,
    RegistroAuditoria,
)


class ModulosVisuaisTests(TestCase):
    def setUp(self):
        self.clinica = Clinica.objects.create(nome="Clínica Fictícia Visual")
        self.user = get_user_model().objects.create_user(
            username="farma.visual", password="Password123456789!"
        )
        self.perfil = PerfilUsuario.objects.create(
            usuario=self.user,
            clinica=self.clinica,
            papel=PerfilUsuario.Papel.ADMINISTRADOR,
            ativo=True,
        )
        self.paciente = Paciente.objects.create(
            clinica=self.clinica,
            nome="PAC-FICT-ORAL-001",
            diagnostico="Cenário fictício",
            data_inicio=date.today(),
        )
        self.medicamento = Medicamento.objects.create(
            clinica=self.clinica,
            nome="Medicamento Oral Fictício",
            principio_ativo="Substância fictícia",
        )
        self.client.login(username="farma.visual", password="Password123456789!")

    def test_cria_agendamento_oral_e_registra_auditoria(self):
        response = self.client.post(
            reverse("medicacoes_orais"),
            {
                "criar_agendamento": "1",
                "paciente": self.paciente.pk,
                "classe": MedicacaoOral.Classe.QUIMIOTERAPIA,
                "medicamento": self.medicamento.pk,
                "data_inicio": date.today().isoformat(),
                "quantidade_ciclos": 6,
                "intervalo_dias": 30,
                "renovacao_pedido_meses": 6,
                "solicitar_guia_antes_dias": 10,
                "estrategia_aquisicao": MedicacaoOral.EstrategiaAquisicao.LISTA_PROGRAMADA,
                "motivo_prioridade": "",
                "observacoes": "Registro inteiramente fictício.",
            },
        )
        self.assertEqual(response.status_code, 302)
        agendamento = MedicacaoOral.objects.get()
        self.assertEqual(
            agendamento.data_proxima_dispensacao,
            date.today(),
        )
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                clinica=self.clinica, acao="Cadastro de dispensação oral"
            ).exists()
        )

    def test_calcula_proxima_dispensacao_de_forma_explicavel(self):
        agendamento = MedicacaoOral.objects.create(
            clinica=self.clinica,
            paciente=self.paciente,
            medicamento=self.medicamento,
            classe=MedicacaoOral.Classe.SUPORTE,
            data_inicio=date(2026, 8, 16),
            quantidade_ciclos=4,
            ciclo_atual=3,
            intervalo_dias=14,
        )
        self.assertEqual(
            agendamento.data_proxima_dispensacao,
            date(2026, 8, 16) + timedelta(days=28),
        )
        self.assertEqual(agendamento.data_renovacao_pedido, date(2027, 2, 16))
        self.assertEqual(len(agendamento.ciclos_previstos), 4)

    def test_configuracoes_somente_admin_e_auditadas(self):
        response = self.client.post(
            reverse("configuracoes"),
            {
                "setor": "Setor Fictício",
                "periodo_padrao_dias": 14,
                "densidade_tabela": ConfiguracaoClinica.DensidadeTabela.COMPACTA,
                "alertar_estoque_minimo": "on",
                "alertar_validade_30_dias": "on",
                "alertar_validacao_pendente": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        configuracao = ConfiguracaoClinica.objects.get(clinica=self.clinica)
        self.assertEqual(configuracao.setor, "Setor Fictício")
        self.assertEqual(configuracao.atualizado_por, self.user)
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                clinica=self.clinica, acao="Alteração de configurações"
            ).exists()
        )

    def test_perfil_leitura_nao_altera_configuracoes(self):
        self.perfil.papel = PerfilUsuario.Papel.LEITURA
        self.perfil.save(update_fields=["papel"])
        response = self.client.post(reverse("configuracoes"), {"setor": "Bloqueado"})
        self.assertEqual(response.status_code, 403)

    def test_paginas_renderizam_barreira_de_decisao_humana(self):
        for nome in ("medicacoes_orais", "configuracoes"):
            response = self.client.get(reverse(nome))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "conferência humana")

    def test_status_oral_exige_perfil_autorizado_e_registra_revisao(self):
        agendamento = MedicacaoOral.objects.create(
            clinica=self.clinica,
            paciente=self.paciente,
            medicamento=self.medicamento,
            classe=MedicacaoOral.Classe.OUTROS,
            data_inicio=date.today(),
        )
        response = self.client.post(
            reverse("medicacoes_orais"),
            {
                "pk": agendamento.pk,
                "atualizar_status": "1",
                "status": MedicacaoOral.Status.PRONTA,
            },
        )
        self.assertEqual(response.status_code, 302)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, MedicacaoOral.Status.PRONTA)
        self.assertEqual(agendamento.revisado_por, self.user)
        self.assertIsNotNone(agendamento.revisado_em)

    def test_preferencia_do_painel_altera_periodo_renderizado(self):
        ConfiguracaoClinica.objects.create(
            clinica=self.clinica,
            periodo_padrao_dias=ConfiguracaoClinica.PeriodoPainel.TRINTA_DIAS,
        )
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "próximos 30 dias")

    def test_filtros_pacientes_medicamentos_e_estoque_sao_reais(self):
        response = self.client.get(reverse("pacientes"), {"busca": "inexistente"})
        self.assertNotContains(response, self.paciente.nome)
        response = self.client.get(
            reverse("medicamentos"), {"busca": "Medicamento Oral Fictício"}
        )
        self.assertContains(response, self.medicamento.nome)
        response = self.client.get(reverse("estoque"), {"busca": "inexistente"})
        self.assertContains(response, "Nenhum lote")

    def test_exportacoes_quantitativo_e_auditoria(self):
        response = self.client.get(
            reverse("quantitativo_csv"),
            {
                "data_inicial": date.today().isoformat(),
                "data_final": date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        response = self.client.get(reverse("auditoria_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Exportação de quantitativo")

    def test_filtro_auditoria_restringe_resultado(self):
        RegistroAuditoria.objects.create(
            clinica=self.clinica,
            usuario=self.user,
            acao="Ação fictícia alfa",
            detalhes="Detalhe local",
        )
        response = self.client.get(reverse("auditoria"), {"busca": "alfa"})
        self.assertContains(response, "Ação fictícia alfa")
        response = self.client.get(reverse("auditoria"), {"busca": "não existe"})
        self.assertContains(response, "Nenhum registro de auditoria")

    def test_exportacoes_pdf_excel_e_backup_sem_credenciais(self):
        ConfiguracaoClinica.objects.get_or_create(clinica=self.clinica)
        response = self.client.get(reverse("relatorios_impressao"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Não substituem avaliação clínica")

        response = self.client.get(reverse("exportar_resumo_excel"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = self.client.get(reverse("backup_seguro"))
        self.assertEqual(response.status_code, 200)
        payload = b"".join(response.streaming_content) if response.streaming else response.content
        texto = payload.decode("utf-8")
        self.assertIn('"segredos_incluidos": false', texto)
        self.assertNotIn("Password123456789!", texto)
        self.assertNotIn("token", texto.lower())
