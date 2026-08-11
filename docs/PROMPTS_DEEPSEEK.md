# PROMPTS_DEEPSEEK.md

## 1. Primeiro diagnóstico do repositório
Leia `DEEPSEEK.md`, `docs/PROJECT_SPEC.md`, `docs/BUSINESS_RULES.md` e `docs/ARCHITECTURE.md`.

Analise o estado REAL do repositório.

NÃO implemente funcionalidades.
NÃO refatore.
NÃO altere código.

Atualize SOMENTE `docs/DEVELOPMENT_STATUS.md` informando:
1. o que já está implementado e funcionando;
2. o que está parcialmente implementado;
3. o que ainda não existe;
4. bugs ou bloqueios encontrados;
5. qual deve ser a próxima Issue de menor escopo e maior prioridade.

## 2. Nova conversa
Leia `DEEPSEEK.md` e `docs/DEVELOPMENT_STATUS.md`. Não faça análise geral do repositório. Trabalhe somente na tarefa que eu enviar.

## 3. Implementar feature
Implemente SOMENTE a Issue #<NÚMERO>.

Regras:
- não ampliar o escopo;
- não refatorar código não relacionado;
- reutilizar componentes existentes;
- não criar dependências sem necessidade;
- executar testes focados;
- atualizar DEVELOPMENT_STATUS.md somente se o status mudar.

Ao final informe apenas: implementação, arquivos alterados, testes e pendências.

## 4. Analisar antes de implementar
Analise SOMENTE a Issue #<NÚMERO>. NÃO altere código.

Entregue apenas: arquivos afetados, regra de negócio, plano mínimo, testes necessários, riscos e dúvidas realmente bloqueantes.

## 5. Corrigir bug
Corrija SOMENTE a Issue #<NÚMERO>. Determine a causa raiz, faça a menor correção segura, adicione teste de regressão e não refatore áreas não relacionadas.

## 6. Revisar PR
Revise SOMENTE o diff. Priorize bugs, regressões, segurança, integridade dos dados, regras de estoque/demanda/sobras e testes ausentes. Ignore refatorações cosméticas.

## 7. Modo econômico
Trabalhe em modo econômico: leia somente arquivos indispensáveis, não repita requisitos, não reproduza arquivos completos, não explique conceitos básicos, não proponha funções adicionais e mantenha a resposta curta.
