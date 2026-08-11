from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from .models import (
    Apresentacao,
    Clinica,
    Medicamento,
    Paciente,
    PerfilUsuario,
    Protocolo,
    SessaoTratamento,
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


class MedicamentoApresentacaoForm(forms.Form):
    nome = forms.CharField(max_length=160, label="Nome do medicamento")
    principio_ativo = forms.CharField(max_length=160, required=False)
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

    def save(self, clinica):
        medicamento, _ = Medicamento.objects.get_or_create(
            clinica=clinica,
            nome=self.cleaned_data["nome"],
            defaults={"principio_ativo": self.cleaned_data["principio_ativo"]},
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
        )


class SessaoTratamentoForm(forms.ModelForm):
    class Meta:
        model = SessaoTratamento
        fields = ["paciente", "protocolo", "data_hora", "ciclo", "dia_ciclo", "status"]
        widgets = {"data_hora": DateTimeInput(format="%Y-%m-%dT%H:%M")}

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
        ]
        widgets = {"data_validade": DateInput()}
        labels = {
            "apresentacao": "Apresentação do medicamento",
            "numero_lote": "Número do lote",
            "data_validade": "Data de validade",
            "quantidade_inicial": "Quantidade inicial (frascos)",
            "estoque_minimo": "Estoque mínimo recomendado",
        }

    def __init__(self, *args, clinica=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Apresentacao
        self.fields["apresentacao"].queryset = Apresentacao.objects.none()
        if clinica:
            self.fields["apresentacao"].queryset = Apresentacao.objects.filter(
                medicamento__clinica=clinica, ativa=True
            ).select_related("medicamento")


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
        fields = ["nome", "principio_ativo", "ativo"]
        labels = {
            "nome": "Nome do medicamento",
            "principio_ativo": "Princípio ativo",
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
            "ativa": "Ativa",
        }

