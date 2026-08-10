from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from .models import Apresentacao, Medicamento, Paciente, Protocolo, SessaoTratamento


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
            "tfg",
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

