# CODEX_WORKFLOW.md — Como trabalhar gastando menos tokens

## Regra
Uma tarefa = uma Issue = uma thread/conversa principal do Codex.

## Fluxo padrão
1. Escolha UMA Issue.
2. Garanta critérios de aceite objetivos.
3. Faça commit do estado atual.
4. Envie ao Codex o prompt curto de implementação.
5. Codex analisa somente arquivos relevantes.
6. Implementa.
7. Executa testes focados.
8. Corrige apenas problemas da tarefa.
9. Atualiza DEVELOPMENT_STATUS.md.
10. Revise o diff.
11. Commit/PR.
12. Abra nova thread para a próxima Issue.

## Quando pedir análise antes
Use análise separada se a tarefa:
- muda banco;
- muda arquitetura;
- afeta vários módulos;
- altera regra crítica de cálculo;
- exige migração;
- tem alto risco de regressão.

Prompt:
"Analise a Issue #X. Não implemente. Identifique arquivos afetados, riscos, testes e plano mínimo."

Depois:
"Implemente o plano aprovado da Issue #X. Não amplie o escopo."

## Quando implementar direto
Para alteração pequena e bem definida:
"Implemente somente a Issue #X. Não explique extensamente. Teste o módulo alterado."

## Para bugs
Forneça:
- comportamento esperado;
- comportamento observado;
- passos mínimos para reproduzir;
- mensagem de erro;
- arquivo/tela relacionada se souber.

Não cole o repositório inteiro.

## Evitar
- "melhore todo o projeto"
- "revise tudo"
- "aproveite e implemente..."
- múltiplas features em um prompt
- colar código que já está no repo
- pedir refatoração e feature simultaneamente
- reexplicar todas as regras em toda conversa

## Revisão de PR
Peça revisão separada da implementação:
"Revise apenas o diff desta PR. Procure bugs, regressões, segurança e violação de BUSINESS_RULES.md. Não proponha refatorações cosméticas."
