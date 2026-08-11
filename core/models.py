from decimal import Decimal
from math import sqrt

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone


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
    ciclos_previstos = models.PositiveSmallIntegerField(default=1, help_text="Quantidade de ciclos previstos para o tratamento")
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    @property
    def superficie_corporal(self):
        """Calcula a superfície corporal usando a fórmula de Mosteller: sqrt((peso * altura) / 3600)"""
        if not self.peso_kg or not self.altura_cm:
            return None
        # Fórmula de Mosteller: SC = sqrt((peso_kg * altura_cm) / 3600)
        resultado = sqrt(float(self.peso_kg) * float(self.altura_cm) / 3600)
        return Decimal(str(round(resultado, 2)))

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

    @property
    def quantidade_reservada(self):
        total = self.movimentacoes.filter(
            tipo=MovimentacaoEstoque.TipoMovimentacao.RESERVA
        ).aggregate(total=Sum("quantidade"))["total"]
        return total or 0

    @property
    def quantidade_disponivel(self):
        return max(0, self.quantidade_atual - self.quantidade_reservada)


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


class PedidoCompra(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        PENDENTE = "pendente", "Pendente de aprovação"
        APROVADO = "aprovado", "Aprovado"
        RECEBIDO = "recebido", "Recebido"
        CANCELADO = "cancelado", "Cancelado"

    clinica = models.ForeignKey(Clinica, on_delete=models.PROTECT, related_name="pedidos_compra")
    numero = models.CharField(max_length=30)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RASCUNHO)
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    fornecedor = models.CharField(max_length=120, blank=True)
    observacao = models.CharField(max_length=500, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    data_recebimento = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(fields=["clinica", "numero"], name="pedido_clinica_numero_unico")
        ]

    def __str__(self):
        return f"{self.numero} ({self.get_status_display()})"

    def gerar_numero(self):
        ano = self.criado_em.year if self.criado_em else timezone.now().year
        sequencia = PedidoCompra.objects.filter(
            clinica=self.clinica, numero__startswith=f"PC-{ano}-"
        ).count() + 1
        return f"PC-{ano}-{sequencia:04d}"


class ItemPedidoCompra(models.Model):
    pedido = models.ForeignKey(PedidoCompra, on_delete=models.CASCADE, related_name="itens")
    apresentacao = models.ForeignKey(Apresentacao, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField()
    quantidade_recebida = models.PositiveIntegerField(default=0)
    custo_unitario = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return f"{self.pedido.numero} — {self.apresentacao} x {self.quantidade}"

    @property
    def restante(self):
        return max(0, self.quantidade - self.quantidade_recebida)


class Transferencia(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        EM_TRANSITO = "em_transito", "Em trânsito"
        RECEBIDA = "recebida", "Recebida"
        CANCELADA = "cancelada", "Cancelada"

    clinica_origem = models.ForeignKey(
        Clinica, on_delete=models.PROTECT, related_name="transferencias_enviadas"
    )
    clinica_destino = models.ForeignKey(
        Clinica, on_delete=models.PROTECT, related_name="transferencias_recebidas"
    )
    numero = models.CharField(max_length=30)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RASCUNHO)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    recebido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    observacao = models.CharField(max_length=500, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    data_recebimento = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinica_origem", "numero"], name="transferencia_origem_numero_unico"
            )
        ]

    def __str__(self):
        return f"{self.numero} ({self.get_status_display()})"

    def gerar_numero(self):
        ano = self.criado_em.year if self.criado_em else timezone.now().year
        sequencia = Transferencia.objects.filter(
            clinica_origem=self.clinica_origem, numero__startswith=f"TR-{ano}-"
        ).count() + 1
        return f"TR-{ano}-{sequencia:04d}"


class ItemTransferencia(models.Model):
    transferencia = models.ForeignKey(
        Transferencia, on_delete=models.CASCADE, related_name="itens"
    )
    apresentacao = models.ForeignKey(Apresentacao, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField()
    quantidade_recebida = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.transferencia.numero} — {self.apresentacao} x {self.quantidade}"

    @property
    def restante(self):
        return max(0, self.quantidade - self.quantidade_recebida)


class SolicitacaoAcesso(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        APROVADA = "aprovada", "Aprovada"
        REJEITADA = "rejeitada", "Rejeitada"

    nome_completo = models.CharField(max_length=180)
    email = models.EmailField()
    clinica = models.ForeignKey(
        Clinica, on_delete=models.SET_NULL, null=True, blank=True, related_name="solicitacoes_acesso"
    )
    papel_solicitado = models.CharField(max_length=20, choices=PerfilUsuario.Papel.choices)
    justificativa = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDENTE)
    analisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    data_hora = models.DateTimeField(auto_now_add=True)
    data_analise = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-data_hora"]

    def __str__(self):
        return f"{self.nome_completo} ({self.email}) — {self.get_status_display()}"


class ImportacaoArquivo(models.Model):
    clinica = models.ForeignKey(Clinica, on_delete=models.PROTECT, related_name="importacoes")
    nome_arquivo = models.CharField(max_length=255)
    aba = models.CharField(max_length=120)
    total_linhas = models.PositiveIntegerField(default=0)
    importadas = models.PositiveIntegerField(default=0)
    com_erro = models.PositiveIntegerField(default=0)
    erros = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_hora"]

    def __str__(self):
        return f"{self.nome_arquivo} — {self.aba} ({self.importadas} importadas)"


