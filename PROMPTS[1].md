# PROMPTS.md

## 1. Prompt padrão — implementação
Leia `AGENTS.md` e `docs/DEVELOPMENT_STATUS.md`.
Consulte apenas a documentação necessária para esta tarefa.

Implemente SOMENTE a Issue #<NÚMERO>.

Regras:
- não ampliar o escopo;
- não refatorar código não relacionado;
- reutilizar componentes existentes;
- não criar dependências sem necessidade;
- executar testes focados;
- atualizar DEVELOPMENT_STATUS.md somente se o status realmente mudou.

Ao final informe apenas:
1. implementação;
2. arquivos alterados;
3. testes;
4. pendências.

## 2. Prompt — análise antes de implementar
Leia `AGENTS.md`.

Analise SOMENTE a Issue #<NÚMERO>.
NÃO altere código.

Entregue:
- arquivos provavelmente afetados;
- regra de negócio envolvida;
- plano mínimo;
- testes necessários;
- riscos;
- dúvidas realmente bloqueantes.

Evite sugerir melhorias fora do escopo.

## 3. Prompt — correção de bug
Leia `AGENTS.md`.

Corrija SOMENTE a Issue #<NÚMERO>.

Primeiro reproduza ou identifique a causa.
Faça a menor correção segura.
Adicione/ajuste teste que prove o bug.
Não refatore áreas não relacionadas.

Ao final:
- causa raiz;
- correção;
- teste;
- arquivos alterados.

## 4. Prompt — revisão de PR
Revise somente o diff desta PR.

Prioridades:
1. bugs;
2. regressões;
3. segurança;
4. integridade dos dados;
5. regras de estoque/demanda/sobras;
6. testes ausentes.

Ignore preferências estéticas sem impacto real.

## 5. Prompt — nova conversa
Leia:
- `AGENTS.md`
- `docs/DEVELOPMENT_STATUS.md`

Não faça uma análise geral do repositório.
Trabalhe apenas na tarefa que eu enviar a seguir.
