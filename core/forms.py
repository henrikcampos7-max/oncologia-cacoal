from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from .models import (
    Apresentacao,
    Clinica,
    ConfiguracaoClinica,
    Lote,
    MedicacaoOral,
    Medicamento,
    Paciente,
    PerfilUsuario,
    Protocolo,
    SessaoTratamento,
    SobraReal,
)


class EmailOuUsuarioAuthenticationForm(AuthenticationForm):
    """Aceita e-mail somente quando ele identifica exatamente um usuário."""

    def clean(self):
        identificador = self.data.get("username", "").strip()
        if "@" in identificador:
            usuarios = get_user_model()._default_manager.filter(email__iexact=identificador)
            if usuarios.count() == 1:
                dados = self.data.copy()
                dados["username"] = usuarios.first().get_username()
                self.data = dados
        return super().clean()


class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            "nome",
            "diagnostico",
            "protocolo",
            "data_inicio",
            "peso_kg",
            "altura_cm",
            "sexo",
            "ciclos_previstos",
        ]
        widgets = {"data_inicio": DateInput()}

    def __init__(self, *args, clinica=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["protocolo"].queryset = Protocolo.objects.none()
        if clinica:
            self.fields["protocolo"].queryset = clinica.protocolos.filter(ativo=True)


class PacienteEdicaoForm(PacienteForm):
    class Meta(PacienteForm.Meta):
        fields = PacienteForm.Meta.fields + ["ativo"]

    def __init__(self, *args, pode_alterar_ativo=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not pode_alterar_ativo:
            self.fields.pop("ativo", None)


class MedicamentoApresentacaoForm(forms.Form):
    nome = forms.CharField(max_length=160, label="Nome do medicamento")
    principio_ativo = forms.CharField(max_length=160, required=False)
    observacoes_medicamento = forms.CharField(
        max_length=500,
        required=False,
        label="Observações do medicamento",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    concentracao = forms.CharField(max_length=80, help_text="Ex.: 1 mg/mL")
    apresentacao = forms.CharField(max_length=120, help_text="Ex.: Frasco 50 mg")
    quantidade_mg = forms.DecimalField(
        min_value=0.001, max_digits=12, decimal_places=3, label="mg por frasco"
    )
    estabilidade_apos_abertura = forms.DecimalField(
        max_digits=6,
        decimal_places=1,
        required=False,
        label="Estabilidade após abertura",
        help_text="Horas ou dias (vazio = não cadastrada; 0 = não reaproveitável).",
    )
    unidade_estabilidade = forms.ChoiceField(
        choices=Apresentacao.UnidadeEstabilidade.choices,
        initial=Apresentacao.UnidadeEstabilidade.HORAS,
        label="Unidade da estabilidade",
    )
    condicoes_armazenamento = forms.CharField(
        max_length=200, required=False, label="Condições de armazenamento"
    )
    observacoes_estabilidade = forms.CharField(
        max_length=300, required=False, label="Observações de estabilidade"
    )
    fonte_referencia = forms.CharField(
        max_length=200, required=False, label="Fonte/referência"
    )
    observacoes = forms.CharField(
        max_length=500,
        required=False,
        label="Outras observações da apresentação",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def save(self, clinica):
        medicamento, _ = Medicamento.objects.get_or_create(
            clinica=clinica,
            nome=self.cleaned_data["nome"],
            defaults={
                "principio_ativo": self.cleaned_data["principio_ativo"],
                "observacoes": self.cleaned_data.get("observacoes_medicamento", ""),
            },
        )
        return Apresentacao.objects.create(
            medicamento=medicamento,
            concentracao=self.cleaned_data["concentracao"],
            descricao=self.cleaned_data["apresentacao"],
            quantidade_mg=self.cleaned_data["quantidade_mg"],
            estabilidade_apos_abertura=self.cleaned_data.get("estabilidade_apos_abertura"),
            unidade_estabilidade=self.cleaned_data.get("unidade_estabilidade", Apresentacao.UnidadeEstabilidade.HORAS),
            condicoes_armazenamento=self.cleaned_data.get("condicoes_armazenamento", ""),
            observacoes_estabilidade=self.cleaned_data.get("observacoes_estabilidade", ""),
            fonte_referencia=self.cleaned_data.get("fonte_referencia", ""),
            observacoes=self.cleaned_data.get("observacoes", ""),
        )


class SessaoTratamentoForm(forms.ModelForm):
    class Meta:
        model = SessaoTratamento
        fields = [
            "paciente",
            "protocolo",
            "data_hora",
            "ciclo",
            "dia_ciclo",
            "observacoes",
        ]
        widgets = {
            "data_hora": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, clinica=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["paciente"].queryset = Paciente.objects.none()
        self.fields["protocolo"].queryset = Protocolo.objects.none()
        if clinica:
            self.fields["paciente"].queryset = clinica.pacientes.filter(ativo=True)
            self.fields["protocolo"].queryset = clinica.protocolos.filter(ativo=True)


class PeriodoForm(forms.Form):
    data_inicial = forms.DateField(widget=DateInput())
    data_final = forms.DateField(widget=DateInput())


class MedicacaoOralForm(forms.ModelForm):
    quantidade_por_ciclo = forms.IntegerField(
        min_value=1,
        initial=1,
        required=False,
        label="Unidades da apresentação por ciclo",
        help_text="Informe unidades de estoque da apresentação escolhida, como caixas ou frascos; não informe comprimidos se o estoque é controlado por caixa.",
    )

    class Meta:
        model = MedicacaoOral
        fields = [
            "paciente",
            "classe",
            "medicamento",
            "apresentacao",
            "dose_prescrita",
            "posologia",
            "quantidade_por_ciclo",
            "data_inicio",
            "quantidade_ciclos",
            "intervalo_dias",
            "renovacao_pedido_meses",
            "solicitar_guia_antes_dias",
            "estrategia_aquisicao",
            "motivo_prioridade",
            "observacoes",
        ]
        widgets = {
            "data_inicio": DateInput(),
            "posologia": forms.Textarea(attrs={"rows": 2}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "apresentacao": "Apresentação prevista",
            "dose_prescrita": "Dose prescrita",
            "posologia": "Posologia",
            "quantidade_por_ciclo": "Unidades da apresentação por ciclo",
            "quantidade_ciclos": "Quantidade de ciclos previstos",
            "intervalo_dias": "Intervalo entre dispensações (dias)",
            "renovacao_pedido_meses": "Renovação do pedido médico (meses)",
            "solicitar_guia_antes_dias": "Solicitar guia antes da entrega (dias)",
            "estrategia_aquisicao": "Estratégia de aquisição",
            "motivo_prioridade": "Motivo da prioridade (opcional)",
        }

    def __init__(self, *args, clinica=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["paciente"].queryset = Paciente.objects.none()
        self.fields["medicamento"].queryset = Medicamento.objects.none()
        self.fields["apresentacao"].queryset = Apresentacao.objects.none()
        if clinica:
            self.fields["paciente"].queryset = clinica.pacientes.filter(ativo=True)
            self.fields["medicamento"].queryset = clinica.medicamentos.filter(ativo=True)
            self.fields["apresentacao"].queryset = Apresentacao.objects.filter(
                medicamento__clinica=clinica, ativa=True
            ).select_related("medicamento")

    def clean(self):
        cleaned = super().clean()
        cleaned["quantidade_por_ciclo"] = cleaned.get("quantidade_por_ciclo") or 1
        paciente = cleaned.get("paciente")
        medicamento = cleaned.get("medicamento")
        apresentacao = cleaned.get("apresentacao")
        ciclo_atual = cleaned.get("ciclo_atual")
        quantidade_ciclos = cleaned.get("quantidade_ciclos")
        if paciente and medicamento and paciente.clinica_id != medicamento.clinica_id:
            raise forms.ValidationError("Paciente e medicamento devem pertencer à mesma clínica.")
        if apresentacao and medicamento and apresentacao.medicamento_id != medicamento.pk:
            self.add_error(
                "apresentacao",
                "A apresentação selecionada deve pertencer ao medicamento informado.",
            )
        if ciclo_atual and quantidade_ciclos and ciclo_atual > quantidade_ciclos:
            self.add_error(
                "ciclo_atual",
                "O ciclo atual não pode ser maior que a quantidade prevista.",
            )
        return cleaned


class MedicacaoOralEdicaoForm(MedicacaoOralForm):
    motivo_alteracao = forms.CharField(
        max_length=300,
        label="Motivo da alteração",
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Obrigatório para preservar a rastreabilidade da mudança.",
    )

    class Meta(MedicacaoOralForm.Meta):
        fields = MedicacaoOralForm.Meta.fields + ["ciclo_atual"]
        labels = {
            **MedicacaoOralForm.Meta.labels,
            "ciclo_atual": "Ciclo atual",
        }


class ConfiguracaoClinicaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoClinica
        fields = [
            "setor",
            "periodo_padrao_dias",
            "densidade_tabela",
            "alertar_estoque_minimo",
            "alertar_validade_30_dias",
            "alertar_validacao_pendente",
        ]
        labels = {
            "periodo_padrao_dias": "Período padrão do painel",
            "densidade_tabela": "Densidade das tabelas",
            "alertar_estoque_minimo": "Alertar estoque mínimo",
            "alertar_validade_30_dias": "Alertar validade em até 30 dias",
            "alertar_validacao_pendente": "Alertar validação pendente",
        }


class SobraRealForm(forms.ModelForm):
    class Meta:
        model = SobraReal
        fields = [
            "apresentacao",
            "quantidade_mg",
            "lote",
            "paciente_origem",
            "data_abertura",
            "condicoes_armazenamento",
        ]
        widgets = {"data_abertura": DateTimeInput(format="%Y-%m-%dT%H:%M")}

    def __init__(self, *args, clinica=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["apresentacao"].queryset = Apresentacao.objects.none()
        self.fields["lote"].queryset = Lote.objects.none()
        self.fields["paciente_origem"].queryset = Paciente.objects.none()
        if clinica:
            self.fields["apresentacao"].queryset = Apresentacao.objects.filter(
                medicamento__clinica=clinica, ativa=True
            )
            self.fields["lote"].queryset = clinica.lotes.filter(ativo=True)
            self.fields["paciente_origem"].queryset = clinica.pacientes.filter(ativo=True)

    def save(self, commit=True, usuario=None, clinica=None):
        sobra = super().save(commit=False)
        sobra.limite_estabilidade = sobra.apresentacao.limite_estabilidade_desde(
            sobra.data_abertura
        )
        if clinica:
            sobra.clinica = clinica
        if usuario:
            sobra.criada_por = usuario
        if commit:
            sobra.save()
        return sobra

    def clean(self):
        cleaned = super().clean()
        inicial, final = cleaned.get("data_inicial"), cleaned.get("data_final")
        if inicial and final and final < inicial:
            raise forms.ValidationError("A data final deve ser igual ou posterior à inicial.")
        return cleaned


class LoteForm(forms.ModelForm):
    class Meta:
        from .models import Lote
        model = Lote
        fields = [
            "apresentacao",
            "numero_lote",
            "data_validade",
            "quantidade_inicial",
            "estoque_minimo",
            "observacoes",
        ]
        widgets = {"data_validade": DateInput()}
        labels = {
            "apresentacao": "Apresentação do medicamento",
            "numero_lote": "Número do lote",
            "data_validade": "Data de validade",
            "quantidade_inicial": "Quantidade inicial (frascos)",
            "estoque_minimo": "Estoque mínimo recomendado",
            "observacoes": "Observações do lote",
        }

    def __init__(self, *args, clinica=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.clinica = clinica
        from .models import Apresentacao
        self.fields["apresentacao"].queryset = Apresentacao.objects.none()
        if clinica:
            self.fields["apresentacao"].queryset = Apresentacao.objects.filter(
                medicamento__clinica=clinica, ativa=True
            ).select_related("medicamento")

    def clean(self):
        cleaned = super().clean()
        apresentacao = cleaned.get("apresentacao")
        numero_lote = cleaned.get("numero_lote")
        if self.clinica and apresentacao and numero_lote:
            duplicados = Lote.objects.filter(
                clinica=self.clinica,
                apresentacao=apresentacao,
                numero_lote__iexact=numero_lote.strip(),
            )
            if self.instance.pk:
                duplicados = duplicados.exclude(pk=self.instance.pk)
            if duplicados.exists():
                self.add_error("numero_lote", "Este lote já está cadastrado para a apresentação.")
        if self.instance.pk:
            possui_historico = (
                self.instance.quantidade_atual > 0
                or self.instance.movimentacoes.exists()
            )
            if "apresentacao" in self.changed_data and possui_historico:
                self.add_error(
                    "apresentacao",
                    "A apresentação não pode ser trocada após existir saldo ou movimentação.",
                )
            if (
                cleaned.get("ativo") is False
                and (
                    self.instance.quantidade_atual > 0
                    or self.instance.quantidade_reservada > 0
                )
            ):
                self.add_error(
                    "ativo",
                    "Zere o saldo e as reservas por movimentações auditáveis antes de desativar o lote.",
                )
        return cleaned


class LoteEdicaoForm(LoteForm):
    class Meta(LoteForm.Meta):
        fields = [
            "apresentacao",
            "numero_lote",
            "data_validade",
            "estoque_minimo",
            "observacoes",
            "ativo",
        ]
        labels = {
            **LoteForm.Meta.labels,
            "ativo": "Lote ativo",
        }


class MovimentacaoEstoqueForm(forms.ModelForm):
    class Meta:
        from .models import MovimentacaoEstoque
        model = MovimentacaoEstoque
        fields = ["lote", "tipo", "quantidade", "observacao"]
        labels = {
            "lote": "Lote de medicamento",
            "tipo": "Tipo de movimentação",
            "quantidade": "Quantidade de frascos",
            "observacao": "Observação / Justificativa",
        }

    def __init__(self, *args, clinica=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Lote
        self.fields["lote"].queryset = Lote.objects.none()
        if clinica:
            self.fields["lote"].queryset = clinica.lotes.filter(ativo=True).select_related(
                "apresentacao__medicamento"
            )


class MedicamentoForm(forms.ModelForm):
    class Meta:
        model = Medicamento
        fields = ["nome", "principio_ativo", "observacoes", "ativo"]
        labels = {
            "nome": "Nome do medicamento",
            "principio_ativo": "Princípio ativo",
            "observacoes": "Observações",
            "ativo": "Ativo",
        }


class ProtocoloForm(forms.ModelForm):
    class Meta:
        from .models import Protocolo
        model = Protocolo
        fields = ["nome", "diagnostico_referencia", "intervalo_dias", "total_ciclos", "ativo"]
        labels = {
            "nome": "Nome do protocolo",
            "diagnostico_referencia": "Diagnóstico de referência",
            "intervalo_dias": "Intervalo entre ciclos (dias)",
            "total_ciclos": "Total de ciclos",
            "ativo": "Ativo",
        }


class ItemProtocoloForm(forms.ModelForm):
    class Meta:
        from .models import ItemProtocolo
        model = ItemProtocolo
        fields = ["apresentacao", "ciclos", "dias_ciclo", "tipo_dose", "dose_valor"]
        labels = {
            "apresentacao": "Medicamento / Apresentação",
            "ciclos": "Ciclos (ex.: 1, 2, 3)",
            "dias_ciclo": "Dias do ciclo (ex.: 1, 15)",
            "tipo_dose": "Tipo de dose",
            "dose_valor": "Valor da dose",
        }

    def __init__(self, *args, clinica=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Apresentacao
        self.fields["apresentacao"].queryset = Apresentacao.objects.none()
        if clinica:
            self.fields["apresentacao"].queryset = Apresentacao.objects.filter(
                medicamento__clinica=clinica, ativa=True
            ).select_related("medicamento")


class SolicitacaoAcessoForm(forms.ModelForm):
    class Meta:
        from .models import SolicitacaoAcesso
        model = SolicitacaoAcesso
        fields = ["nome_completo", "email", "clinica", "papel_solicitado", "justificativa"]
        labels = {
            "nome_completo": "Nome completo",
            "email": "E-mail",
            "clinica": "Clínica",
            "papel_solicitado": "Perfil desejado",
            "justificativa": "Justificativa",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["clinica"].queryset = Clinica.objects.filter(ativa=True)
        self.fields["clinica"].required = False
        self.fields["justificativa"].required = False


class ImportacaoArquivoForm(forms.Form):
    arquivo = forms.FileField(
        label="Arquivo XLSX",
        help_text="Somente arquivos .xlsx são aceitos.",
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        if not arquivo.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Formato inválido. Envie um arquivo .xlsx.")
        if arquivo.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Arquivo muito grande (máximo 10 MB).")
        return arquivo


class ApresentacaoForm(forms.ModelForm):
    class Meta:
        model = Apresentacao
        fields = [
            "concentracao",
            "descricao",
            "quantidade_mg",
            "estabilidade_apos_abertura",
            "unidade_estabilidade",
            "condicoes_armazenamento",
            "observacoes_estabilidade",
            "fonte_referencia",
            "observacoes",
            "ativa",
        ]
        labels = {
            "concentracao": "Concentração",
            "descricao": "Descrição",
            "quantidade_mg": "Quantidade (mg)",
            "estabilidade_apos_abertura": "Estabilidade após abertura",
            "unidade_estabilidade": "Unidade da estabilidade",
            "condicoes_armazenamento": "Condições de armazenamento",
            "observacoes_estabilidade": "Observações de estabilidade",
            "fonte_referencia": "Fonte/referência",
            "observacoes": "Outras observações",
            "ativa": "Ativa",
        }

