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

## Segurança

- Não incluir dados reais de pacientes, prescrições, credenciais ou planilhas operacionais.
- Usar somente dados fictícios em desenvolvimento e testes.
- O sistema deve apoiar rotinas administrativas e não tomar decisões clínicas.
- Alterações de dose, estoque, compra ou cadastro exigem validação humana.

Consulte [SECURITY.md](SECURITY.md) antes de adicionar dados ou integrações.

## Próximos passos

1. Revisar requisitos e modelo de dados.
2. Criar a estrutura inicial da aplicação.
3. Adicionar dados fictícios e testes.
4. Validar fluxos com responsáveis humanos antes de qualquer uso operacional.
