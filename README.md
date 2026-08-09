# Oncologia Cacoal

Projeto em fase de planejamento de um MVP administrativo para previsão de demanda, controle de estoque e apoio às compras de medicamentos oncológicos.

## Escopo previsto

- importação e validação de dados;
- agenda e tratamentos;
- medicamentos e apresentações;
- estoque, movimentações, lotes e validade;
- reservas, compras e alertas;
- auditoria e relatórios.

## Estado atual

O repositório contém documentação funcional, identidade visual e uma ferramenta de inspeção estrutural de planilhas. A aplicação ainda não foi implementada nem publicada.

## Como executar

Pré-requisito: Python 3.11+.

```bash
python tools/inspect_xlsx_structure.py <arquivo.xlsx> <saida.json>
```

Exemplo:

```bash
python tools/inspect_xlsx_structure.py /caminho/previsao.xlsx /tmp/relatorio.json
```

## Comportamento de validações e erros

A ferramenta retorna códigos previsíveis:

- `0`: execução com sucesso;
- `2`: erro de validação de entrada (`VALIDATION_ERROR`);
- `1`: falha interna inesperada (`INTERNAL_ERROR`).

Validações básicas:

- arquivo de entrada obrigatório, existente e com extensão `.xlsx`;
- arquivo de saída com extensão `.json`;
- diretório de saída deve existir.

Em falhas internas, a execução registra log de exceção e retorna erro padronizado em JSON no `stderr`.

## Núcleo inicial de importação e validação

Arquivo: `tools/import_preview.py`

O repositório agora inclui um núcleo inicial para a pendência de **importações e validação da previsão**. Esta etapa cobre:

- sugestão automática de mapeamento de colunas para o layout inicial da aba `Aplicacoes`;
- contrato persistível para salvar e recarregar modelos de mapeamento;
- prévia de importação com classificação por linha em `valid`, `requires_review`, `error`, `duplicate` e `rejected`;
- validações explícitas para paciente, medicamento, data de início, dose, intervalo, unidade, ciclos, aplicações por ciclo e status.

Exemplo curto:

```python
from tools.import_preview import preview_forecast_import, suggest_column_mapping

mapping = suggest_column_mapping(
    [
        "Plano",
        "Paciente",
        "Medicamento",
        "Início do tratamento",
        "Intervalo do ciclo em dias",
        "Dose por ciclo",
        "Unidade",
        "Quantidade de ciclos previstos",
        "Aplicações por ciclo",
        "Status",
    ]
)

preview = preview_forecast_import(
    rows=[...],
    field_mapping=mapping,
    reference_date="2026-08-10",
)
```

## Núcleo inicial de cálculo (demanda/estoque/compras)

Arquivo: `tools/calculate_purchase_plan.py`

Regras explícitas desta versão:

- demanda mensal é agregada por `medication` + mês (`YYYY-MM`);
- somente aplicações com status ativo (`ativo`/`active`) entram no cálculo;
- projeção de compra mensal usa `max(0, demanda - saldo_abertura)`;
- o saldo de fechamento de um mês é carregado para o mês seguinte.

Exemplo curto:

```python
from tools.calculate_purchase_plan import (
    DemandRecord,
    build_purchase_plan_snapshot,
    calculate_purchase_plan,
    purchase_plan_snapshot_to_dict,
)

plan = calculate_purchase_plan(
    initial_stock={"Medicamento A": 120},
    monthly_demand=[
        DemandRecord("Medicamento A", "2026-08", 100),
        DemandRecord("Medicamento A", "2026-09", 70),
    ],
)

snapshot = build_purchase_plan_snapshot(
    initial_stock={"Medicamento A": 120},
    monthly_demand=[
        DemandRecord("Medicamento A", "2026-08", 100),
        DemandRecord("Medicamento A", "2026-09", 70),
    ],
)
payload = purchase_plan_snapshot_to_dict(snapshot)
```

Contrato persistível básico do cálculo:

- `meta.schema_version`: versão do contrato (`purchase-plan.v1`);
- `meta.calculation_id`: identificador do cálculo persistido;
- `meta.generated_at`: data/hora UTC de geração;
- `meta.status`: estado inicial do snapshot (`draft`);
- `meta.review_required`: indica necessidade de validação humana;
- `initial_stock`: lista normalizada de `{medication, amount}`;
- `monthly_demand`: lista normalizada de `{medication, month, amount}`;
- `projections`: saída mensal de `{medication, month, opening_stock, demand, suggested_purchase, closing_stock}`.

Ao recarregar um snapshot, o contrato valida duplicidades e consistência básica do cálculo antes de aceitar os dados persistidos.

## Segurança

- Não incluir dados reais de pacientes, prescrições, credenciais ou planilhas operacionais.
- Usar somente dados fictícios em desenvolvimento e testes.
- O sistema deve apoiar rotinas administrativas e não tomar decisões clínicas.
- Alterações de dose, estoque, compra ou cadastro exigem validação humana.

Consulte [SECURITY.md](SECURITY.md) antes de adicionar dados ou integrações.

## Próximos passos

1. Criar a estrutura inicial da aplicação.
2. Expandir a importação de estoque com conciliação e justificativa de ajuste.
3. Adicionar dados fictícios e testes de integração dos fluxos de importação.
4. Validar fluxos com responsáveis humanos antes de qualquer uso operacional.
