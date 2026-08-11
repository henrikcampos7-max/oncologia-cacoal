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
    class UnidadeEstabilidade(models.TextChoices):
        HORAS = "horas", "Horas"
        DIAS = "dias", "Dias"

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
    estabilidade_apos_abertura = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Estabilidade após abertura/reconstituição. Deixe vazio se não houver valor de referência cadastrado.",
    )
    unidade_estabilidade = models.CharField(
        max_length=10,
        choices=UnidadeEstabilidade.choices,
        default=UnidadeEstabilidade.HORAS,
    )
    condicoes_armazenamento = models.CharField(
        max_length=200, blank=True, help_text="Ex.: Refrigerar entre 2 °C e 8 °C."
    )
    observacoes_estabilidade = models.CharField(
        max_length=300, blank=True, help_text="Observações de manipulação/reconstituição."
    )
    fonte_referencia = models.CharField(
        max_length=200, blank=True, help_text="Fonte/bula/referência da estabilidade."
    )
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["medicamento__nome", "quantidade_mg"]

    def __str__(self):
        return f"{self.medicamento} — {self.descricao}"

    @property
    def estabilidade_cadastrada(self):
        if self.estabilidade_apos_abertura is None:
            return False
        return self.estabilidade_apos_abertura > 0

    def limite_estabilidade_desde(self, data_hora):
        """Data/hora limite de estabilidade a partir da abertura (None se não cadastrada)."""
        if not self.estabilidade_cadastrada:
            return None
        from datetime import timedelta

        valor = self.estabilidade_apos_abertura
        if self.unidade_estabilidade == self.UnidadeEstabilidade.DIAS:
            dias = float(valor)
        else:
            dias = float(valor) / 24
        return data_hora + timedelta(days=dias)


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
        FALTOU = "faltou", "Faltou / Não compareceu"

    clinica = models.ForeignKey(Clinica, on_delete=models.PROTECT, related_name="sessoes")
    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name="sessoes")
    protocolo = models.ForeignKey(Protocolo, on_delete=models.PROTECT, related_name="sessoes")
    data_hora = models.DateTimeField()
    ciclo = models.PositiveSmallIntegerField(default=1)
    dia_ciclo = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AGENDADA)
    motivo = models.CharField(
        max_length=300,
        blank=True,
        help_text="Motivo de falta ou cancelamento, quando aplicável.",
    )
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

    class StatusConferencia(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        RELATORIO_IMPORTADO = "relatorio_importado", "Relatório importado"
        EM_TRANSITO = "em_transito", "Em trânsito"
        AGUARDANDO_RECEBIMENTO = "aguardando_recebimento", "Aguardando recebimento"
        EM_CONFERENCIA = "em_conferencia", "Em conferência"
        PENDENCIA_MANUAL = "pendencia_manual", "Pendência manual"
        DIVERGENCIA = "divergencia", "Divergência"
        PRONTA_PARA_APROVACAO = "pronta_para_aprovacao", "Pronta para aprovação"
        APROVADA = "aprovada", "Aprovada"
        INTEGRADA_AO_ESTOQUE = "integrada_ao_estoque", "Integrada ao estoque"
        CANCELADA = "cancelada", "Cancelada"

    clinica_origem = models.ForeignKey(
        Clinica, on_delete=models.PROTECT, related_name="transferencias_enviadas"
    )
    clinica_destino = models.ForeignKey(
        Clinica, on_delete=models.PROTECT, related_name="transferencias_recebidas"
    )
    numero = models.CharField(max_length=30)
    importada = models.BooleanField(
        default=False,
        help_text="Verdadeiro quando a transferência veio de importação de planilha (Ji-Paraná).",
    )
    relatorio_arquivo = models.FileField(
        upload_to="transferencias/relatorios/",
        null=True,
        blank=True,
        help_text="PDF original do relatório de transferência (Ji-Paraná).",
    )
    hash_relatorio = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 do arquivo do relatório (evita importação duplicada).",
    )
    data_relatorio = models.DateField(
        null=True,
        blank=True,
        help_text="Data de emissão do relatório de transferência.",
    )
    referencia_externa = models.CharField(
        max_length=120,
        blank=True,
        help_text="Número identificador do documento / referência externa.",
    )
    status_conferencia = models.CharField(
        max_length=30,
        choices=StatusConferencia.choices,
        default=StatusConferencia.RASCUNHO,
        help_text="Estado do fluxo de conferência automatizada do recebimento.",
    )
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


class StatusReconciliacao(models.TextChoices):
    """Status da conferência automatizada de itens de transferência (SKILLS 17–22)."""

    CONFORME = "conforme", "Conforme"
    NAO_FOTOGRAFADO = "nao_fotografado", "Não fotografado"
    CONFERENCIA_MANUAL = "conferencia_manual", "Conferência manual"
    DIVERGENCIA_PRODUTO = "divergencia_produto", "Divergência de produto"
    DIVERGENCIA_APRESENTACAO = "divergencia_apresentacao", "Divergência de apresentação"
    DIVERGENCIA_LOTE = "divergencia_lote", "Divergência de lote"
    DIVERGENCIA_QUANTIDADE = "divergencia_quantidade", "Divergência de quantidade"
    VALIDADE_NAO_IDENTIFICADA = "validade_nao_identificada", "Validade não identificada"
    VALIDADE_CRITICA = "validade_critica", "Validade crítica"
    DIVERGENCIA_VALIDADE = "divergencia_validade", "Validade divergente/vencida"
    ITEM_NAO_PREVISTO = "item_nao_previsto", "Item não previsto"
    POSSIVEL_DUPLICIDADE = "possivel_duplicidade", "Possível duplicidade"
    FOTO_INSUFICIENTE = "foto_insuficiente", "Foto insuficiente"


class ItemTransferencia(models.Model):
    transferencia = models.ForeignKey(
        Transferencia, on_delete=models.CASCADE, related_name="itens"
    )
    apresentacao = models.ForeignKey(Apresentacao, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField()
    quantidade_recebida = models.PositiveIntegerField(default=0)
    status_reconciliacao = models.CharField(
        max_length=28,
        choices=StatusReconciliacao.choices,
        default=StatusReconciliacao.NAO_FOTOGRAFADO,
        help_text="Status da conferência automatizada (mantido em sincronia com a reconciliação).",
    )
    lote_esperado = models.CharField(
        max_length=80,
        blank=True,
        help_text="Lote informado no relatório de transferência (Ji-Paraná).",
    )
    tipo_insumo = models.CharField(
        max_length=60,
        blank=True,
        help_text="Seção do relatório: Medicamento, Material de Enfermagem, Solução etc.",
    )

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
    class Tipo(models.TextChoices):
        MEDICAMENTOS = "medicamentos", "Medicamentos"
        GMED = "gmed", "GMED"
        TRANSFERENCIAS = "transferencias", "Transferências"

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.MEDICAMENTOS,
        help_text="Origem/destino da importação (catálogo, GMED ou transferências de Ji-Paraná).",
    )
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


class SobraReal(models.Model):
    """Sobra fisicamente existente após uma manipulação/atendimento realizado.

    Nunca altera o estoque físico; é usada para rastreabilidade operacional e,
    quando disponível, entra no pool do motor de sobras projetadas via
    `sobras_iniciais`.
    """

    class Status(models.TextChoices):
        DISPONIVEL = "disponivel", "Disponível"
        REUTILIZADA = "reutilizada", "Reutilizada"
        EXPIROU = "expirada", "Expirada"
        DESCARTADA = "descartada", "Descartada"

    clinica = models.ForeignKey(
        Clinica, on_delete=models.PROTECT, related_name="sobras_reais"
    )
    apresentacao = models.ForeignKey(
        Apresentacao, on_delete=models.PROTECT, related_name="sobras_reais"
    )
    quantidade_mg = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Quantidade de sobra em mg.",
    )
    lote = models.ForeignKey(
        Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name="sobras_reais"
    )
    paciente_origem = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sobras_geradas",
    )
    data_abertura = models.DateTimeField()
    limite_estabilidade = models.DateTimeField(
        null=True, blank=True, help_text="Calculado a partir da estabilidade cadastrada da apresentação."
    )
    condicoes_armazenamento = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DISPONIVEL)
    paciente_destino = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sobras_recebidas",
    )
    data_reutilizacao = models.DateTimeField(null=True, blank=True)
    motivo_descarte = models.CharField(max_length=300, blank=True)
    data_descarte = models.DateTimeField(null=True, blank=True)
    criada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]

    def __str__(self):
        return f"{self.apresentacao} — {self.quantidade_mg} mg ({self.get_status_display()})"

    @property
    def dentro_da_estabilidade(self):
        if self.limite_estabilidade is None:
            return False
        return timezone.now() <= self.limite_estabilidade

    def reutilizar(self, paciente_destino, usuario):
        if self.status != self.Status.DISPONIVEL:
            raise ValueError("Somente sobras disponíveis podem ser reutilizadas.")
        if not self.dentro_da_estabilidade:
            raise ValueError("Sobra fora do prazo de estabilidade.")
        self.status = self.Status.REUTILIZADA
        self.paciente_destino = paciente_destino
        self.data_reutilizacao = timezone.now()
        self.save(update_fields=["status", "paciente_destino", "data_reutilizacao"])
        RegistroAuditoria.objects.create(
            clinica=self.clinica,
            usuario=usuario,
            acao=f"Reutilizou sobra {self.pk} de {self.apresentacao} para {paciente_destino.nome}.",
            detalhes=f"quantidade_mg={self.quantidade_mg}; lote={self.lote or '-'}",
        )

    def descartar(self, motivo, usuario):
        if self.status != self.Status.DISPONIVEL:
            raise ValueError("Somente sobras disponíveis podem ser descartadas.")
        self.status = self.Status.DESCARTADA
        self.motivo_descarte = motivo
        self.data_descarte = timezone.now()
        self.save(update_fields=["status", "motivo_descarte", "data_descarte"])
        RegistroAuditoria.objects.create(
            clinica=self.clinica,
            usuario=usuario,
            acao=f"Descartou sobra {self.pk} de {self.apresentacao}.",
            detalhes=f"motivo={motivo or '-'}; quantidade_mg={self.quantidade_mg}",
        )


class AliasMedicamento(models.Model):
    """Tabela de aliases aprovados: vincula nomes usados nos relatórios de
    transferência ao cadastro mestre da clínica (SKILL 04 — resolve_product_alias).
    """

    clinica = models.ForeignKey(
        Clinica, on_delete=models.PROTECT, related_name="aliases_medicamento"
    )
    alias = models.CharField(
        max_length=160,
        help_text="Nome/descrição como aparece no relatório de transferência.",
    )
    medicamento = models.ForeignKey(
        Medicamento, on_delete=models.PROTECT, related_name="aliases"
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["alias"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "alias"], name="alias_medicamento_unico_por_clinica"
            )
        ]

    def __str__(self):
        return f"{self.alias} → {self.medicamento.nome}"


class TransferenciaEvidencia(models.Model):
    """Evidência fotográfica do recebimento (SKILL 06/07/16).

    Preserva o arquivo original; o conteúdo extraído fica em ExtracaoEvidencia.
    """

    class StatusProcessamento(models.TextChoices):
        NOVA = "nova", "Nova (aguardando extração)"
        PROCESSANDO = "processando", "Processando"
        EXTRAIDA = "extraida", "Extraída"
        FALHOU = "falhou", "Falhou"
        REQUER_REVISAO = "requer_revisao", "Requere revisão manual"

    transferencia = models.ForeignKey(
        Transferencia, on_delete=models.CASCADE, related_name="evidencias"
    )
    item = models.ForeignKey(
        ItemTransferencia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evidencias",
        help_text="Item provável ao qual a foto pertence (vínculo manual ou por semelhança).",
    )
    arquivo = models.FileField(
        upload_to="transferencias/evidencias/",
        help_text="Foto original da embalagem (nunca substituída).",
    )
    hash_arquivo = models.CharField(max_length=64, help_text="SHA-256 do arquivo.")
    qualidade = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Score de qualidade visual (0 a 1).",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusProcessamento.choices,
        default=StatusProcessamento.NOVA,
    )
    suspeita_duplicidade = models.BooleanField(
        default=False,
        help_text="Marcado quando o hash indica possível envio repetido (nunca exclui automaticamente).",
    )
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]

    def __str__(self):
        return f"Evidência {self.pk} ({self.transferencia.numero})"


class ExtracaoEvidencia(models.Model):
    """Resultado estruturado e versionado da extração visual de uma evidência
    (SKILL 10–14). Um novo processamento cria nova linha: o histórico de versões
    permanece auditável (SKILLS 36/37).
    """

    evidencia = models.ForeignKey(
        TransferenciaEvidencia, on_delete=models.CASCADE, related_name="extracoes"
    )
    nome_produto = models.CharField(max_length=200, blank=True)
    principio_ativo = models.CharField(max_length=200, blank=True)
    apresentacao = models.CharField(max_length=200, blank=True)
    lote = models.CharField(max_length=80, blank=True)
    validade = models.DateField(null=True, blank=True)
    fabricacao = models.DateField(null=True, blank=True)
    quantidade = models.PositiveIntegerField(null=True, blank=True)
    codigo_gs1 = models.CharField(max_length=64, blank=True, help_text="GTIN/GS1 quando decodificado.")
    lote_gs1 = models.CharField(max_length=80, blank=True)
    validade_gs1 = models.DateField(null=True, blank=True)
    confianca_produto = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    confianca_lote = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    confianca_validade = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    confianca_quantidade = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    engine = models.CharField(max_length=60, default="manual", help_text="Provider/modelo usado.")
    versao = models.CharField(max_length=40, default="1")
    resultado_bruto = models.JSONField(default=dict, blank=True)
    requer_revisao = models.BooleanField(default=True)
    extraido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]


class ReconciliacaoItemTransferencia(models.Model):
    """Comparação esperado × observado para um item da transferência
    (SKILLS 17–22). Mantém o que foi decidido/aprovado separado do reportado.
    """

    item = models.OneToOneField(
        ItemTransferencia, on_delete=models.CASCADE, related_name="reconciliacao"
    )
    produto_observado = models.ForeignKey(
        Apresentacao,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reconciliacoes",
    )
    lote_observado = models.CharField(max_length=80, blank=True)
    validade_observada = models.DateField(null=True, blank=True)
    quantidade_observada = models.PositiveIntegerField(null=True, blank=True)
    match_produto = models.BooleanField(null=True)
    match_lote = models.BooleanField(null=True)
    match_quantidade = models.BooleanField(null=True)
    status_validade = models.CharField(max_length=20, blank=True, help_text="ok|critica|desconhecida|vencida")
    status_final = models.CharField(
        max_length=28, choices=StatusReconciliacao.choices, default=StatusReconciliacao.NAO_FOTOGRAFADO
    )
    confianca_final = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    anotacoes = models.CharField(max_length=500, blank=True)
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    revisado_em = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)


class DivergenciaTransferencia(models.Model):
    """Divergência tipada e auditável (SKILL 23/24). Nunca apaga valores originais."""

    class Tipo(models.TextChoices):
        PRODUTO = "produto", "Produto diferente"
        APRESENTACAO = "apresentacao", "Apresentação diferente"
        LOTE = "lote", "Lote diferente"
        QUANTIDADE = "quantidade", "Quantidade diferente"
        VALIDADE = "validade", "Validade"
        ITEM_EXTRA = "item_extra", "Item não previsto no relatório"
        ITEM_AUSENTE = "item_ausente", "Item previsto ausente"
        FOTO_INSUFICIENTE = "foto_insuficiente", "Foto insuficiente"
        DUPLICIDADE = "duplicidade", "Possível duplicidade de evidência"

    class Severidade(models.TextChoices):
        INFORMATIVA = "informativa", "Informativa"
        MEDIA = "media", "Média"
        CRITICA = "critica", "Crítica"

    class StatusResolucao(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        RESOLVIDA = "resolvida", "Resolvida"
        IGNORADA = "ignorada", "Ignorada"

    transferencia = models.ForeignKey(
        Transferencia, on_delete=models.CASCADE, related_name="divergencias"
    )
    item = models.ForeignKey(
        ItemTransferencia, on_delete=models.SET_NULL, null=True, blank=True, related_name="divergencias"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    severidade = models.CharField(max_length=12, choices=Severidade.choices, default=Severidade.MEDIA)
    valor_esperado = models.CharField(max_length=300, blank=True)
    valor_observado = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=12, choices=StatusResolucao.choices, default=StatusResolucao.PENDENTE)
    resolucao = models.CharField(max_length=500, blank=True)
    resolvida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    resolvida_em = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)


