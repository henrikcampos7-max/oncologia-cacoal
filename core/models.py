from decimal import Decimal
from math import sqrt

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Clinica(models.Model):
    nome = models.CharField(max_length=160)
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class PerfilUsuario(models.Model):
    class Papel(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        FARMACEUTICO = "farmaceutico", "Farmacêutico"
        AUXILIAR = "auxiliar", "Auxiliar"
        ENFERMAGEM = "enfermagem", "Enfermagem"
        GESTOR = "gestor", "Gestor"
        LEITURA = "leitura", "Somente leitura"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_oncologia"
    )
    clinica = models.ForeignKey(Clinica, on_delete=models.PROTECT, related_name="perfis")
    papel = models.CharField(max_length=20, choices=Papel.choices, default=Papel.LEITURA)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.usuario} — {self.get_papel_display()}"


class Medicamento(models.Model):
    clinica = models.ForeignKey(Clinica, on_delete=models.PROTECT, related_name="medicamentos")
    nome = models.CharField(max_length=160)
    principio_ativo = models.CharField(max_length=160, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(fields=["clinica", "nome"], name="medicamento_nome_por_clinica")
        ]

    def __str__(self):
        return self.nome


class Apresentacao(models.Model):
    medicamento = models.ForeignKey(
        Medicamento, on_delete=models.PROTECT, related_name="apresentacoes"
    )
    concentracao = models.CharField(max_length=80)
    descricao = models.CharField(max_length=120)
    quantidade_mg = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Quantidade total em mg por frasco/apresentação.",
    )
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["medicamento__nome", "quantidade_mg"]

    def __str__(self):
        return f"{self.medicamento} — {self.descricao}"


class Protocolo(models.Model):
    clinica = models.ForeignKey(Clinica, on_delete=models.PROTECT, related_name="protocolos")
    nome = models.CharField(max_length=120)
    diagnostico_referencia = models.CharField(max_length=180, blank=True)
    intervalo_dias = models.PositiveSmallIntegerField(default=21)
    total_ciclos = models.PositiveSmallIntegerField(default=1)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class ItemProtocolo(models.Model):
    class TipoDose(models.TextChoices):
        FIXA = "fixa", "Dose fixa (mg)"
        MG_KG = "mg_kg", "mg/kg"
        MG_M2 = "mg_m2", "mg/m²"

    protocolo = models.ForeignKey(Protocolo, on_delete=models.CASCADE, related_name="itens")
    apresentacao = models.ForeignKey(Apresentacao, on_delete=models.PROTECT)
    ciclos = models.CharField(max_length=120, default="1", help_text="Ex.: 1, 2, 3, 4")
    dias_ciclo = models.CharField(max_length=120, default="1", help_text="Ex.: 1, 15")
    tipo_dose = models.CharField(max_length=10, choices=TipoDose.choices, default=TipoDose.MG_M2)
    dose_valor = models.DecimalField(
        max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal("0"))]
    )

    def __str__(self):
        return f"{self.protocolo} — {self.apresentacao}"


class Paciente(models.Model):
    class Sexo(models.TextChoices):
        FEMININO = "F", "Feminino"
        MASCULINO = "M", "Masculino"
        OUTRO = "O", "Outro/não informado"

    clinica = models.ForeignKey(Clinica, on_delete=models.PROTECT, related_name="pacientes")
    nome = models.CharField(max_length=180)
    diagnostico = models.CharField(max_length=200, blank=True)
    protocolo = models.ForeignKey(
        Protocolo, on_delete=models.PROTECT, related_name="pacientes", null=True, blank=True
    )
    data_inicio = models.DateField()
    peso_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    altura_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    sexo = models.CharField(max_length=1, choices=Sexo.choices, blank=True)
    tfg = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    @property
    def superficie_corporal(self):
        if not self.peso_kg or not self.altura_cm:
            return None
        return Decimal(str(round(sqrt(float(self.peso_kg * self.altura_cm) / 3600), 2)))

    def __str__(self):
        return self.nome


class SessaoTratamento(models.Model):
    class Status(models.TextChoices):
        AGENDADA = "agendada", "Agendada"
        CONFIRMADA = "confirmada", "Confirmada"
        REALIZADA = "realizada", "Realizada"
        CANCELADA = "cancelada", "Cancelada"

    clinica = models.ForeignKey(Clinica, on_delete=models.PROTECT, related_name="sessoes")
    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name="sessoes")
    protocolo = models.ForeignKey(Protocolo, on_delete=models.PROTECT, related_name="sessoes")
    data_hora = models.DateTimeField()
    ciclo = models.PositiveSmallIntegerField(default=1)
    dia_ciclo = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AGENDADA)
    observacoes = models.CharField(max_length=500, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["data_hora"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "paciente", "data_hora", "ciclo", "dia_ciclo"],
                name="sessao_sem_duplicidade_exata",
            )
        ]

    def __str__(self):
        return f"{self.paciente} — {self.data_hora:%d/%m/%Y %H:%M}"


class Lote(models.Model):
    clinica = models.ForeignKey(Clinica, on_delete=models.PROTECT, related_name="lotes")
    apresentacao = models.ForeignKey(
        Apresentacao, on_delete=models.PROTECT, related_name="lotes"
    )
    numero_lote = models.CharField(max_length=60)
    data_validade = models.DateField()
    quantidade_inicial = models.PositiveIntegerField(default=0)
    quantidade_atual = models.PositiveIntegerField(default=0)
    estoque_minimo = models.PositiveIntegerField(default=5)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["data_validade", "apresentacao__medicamento__nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "apresentacao", "numero_lote"],
                name="lote_unico_por_apresentacao_clinica",
            )
        ]

    def __str__(self):
        return f"{self.apresentacao} — Lote {self.numero_lote} (Val: {self.data_validade:%d/%m/%Y})"

    @property
    def dias_para_vencer(self):
        from django.utils import timezone
        return (self.data_validade - timezone.localdate()).days

    @property
    def status_validade(self):
        dias = self.dias_para_vencer
        if dias < 0:
            return "vencido"
        elif dias <= 30:
            return "critico"
        elif dias <= 90:
            return "alerta"
        return "ok"

    @property
    def status_estoque(self):
        if self.quantidade_atual == 0:
            return "esgotado"
        elif self.quantidade_atual <= self.estoque_minimo:
            return "baixo"
        return "ok"


class MovimentacaoEstoque(models.Model):
    class TipoMovimentacao(models.TextChoices):
        ENTRADA = "entrada", "Entrada / Recebimento"
        SAIDA = "saida", "Saída / Aplicação"
        PERDA = "perda", "Perda / Descarte"
        AJUSTE = "ajuste", "Ajuste de Inventário"
        RESERVA = "reserva", "Reserva"

    clinica = models.ForeignKey(
        Clinica, on_delete=models.PROTECT, related_name="movimentacoes_estoque"
    )
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name="movimentacoes")
    tipo = models.CharField(max_length=20, choices=TipoMovimentacao.choices)
    quantidade = models.IntegerField(help_text="Positivo para entradas, negativo para saídas.")
    sessao = models.ForeignKey(
        SessaoTratamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes_estoque",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    observacao = models.CharField(max_length=255, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_hora"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {abs(self.quantidade)} un. ({self.lote.numero_lote})"


class RegistroAuditoria(models.Model):
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name="auditorias")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    acao = models.CharField(max_length=120)
    detalhes = models.TextField(blank=True)
    ip_origem = models.GenericIPAddressField(null=True, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_hora"]

    def __str__(self):
        return f"[{self.data_hora:%d/%m/%Y %H:%M}] {self.usuario} — {self.acao}"


