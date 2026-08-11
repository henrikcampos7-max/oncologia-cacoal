# DEEPSEEK_WORKFLOW.md

## Regra de ouro
UMA Issue = UMA tarefa = UMA conversa principal.

## Fluxo
1. Escolha uma Issue.
2. Defina critérios de aceite.
3. Faça commit do estado atual.
4. Peça ao DeepSeek somente aquela alteração.
5. Limite a análise aos arquivos relevantes.
6. Implemente.
7. Teste o módulo.
8. Corrija somente o necessário.
9. Atualize DEVELOPMENT_STATUS.md.
10. Revise o diff.
11. Faça commit/PR.
12. Abra nova conversa para a próxima Issue.

## Tarefa grande
Primeiro: “Analise somente a Issue #X. Não implemente. Identifique arquivos, riscos, plano mínimo e testes.”

Depois: “Implemente somente a Issue #X seguindo o plano aprovado.”

## Tarefa pequena
“Implemente somente a Issue #X. Não faça análise geral. Não refatore fora do escopo. Execute apenas testes relacionados.”

## Evitar
“melhore tudo”, “revise o projeto inteiro”, “refatore tudo”, “aproveite e faça também...”, várias features no mesmo prompt e colar código que já está no GitHub.
