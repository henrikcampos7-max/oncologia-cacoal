---
name: oncologia-qa-regressao
description: Planejar e executar QA de regressão para fluxos da Oncologia Cacoal. Usar em testes de agenda, estoque, compras, permissões, auditoria, exportações e interfaces críticas.
---

# QA de regressão oncológica

Aplicar as regras permanentes do repositório e o Modo de Economia de Tokens.

## Fluxo

- Começar por critérios de aceite e testes existentes do módulo.
- Usar exclusivamente dados sintéticos.
- Cobrir caminho feliz, validação, estado vazio, erro, conflito, permissão negada e repetição idempotente.
- Em estoque e compras, testar saldo não negativo, transação, FEFO, confirmação manual e auditoria.
- Em acesso e exportação, testar menor privilégio e ausência de segredos/dados pessoais.
- Rodar testes focados antes da suíte completa e relatar exatamente o executado.

## Saída

Informar somente alteração, arquivos, testes executados e pendências ou riscos reais.
