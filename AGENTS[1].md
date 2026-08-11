# AGENTS.md — Projeto Oncologia Cacoal

## Objetivo
Desenvolver o sistema de gestão oncológica com foco em segurança, rastreabilidade, estoque, agenda, previsão de demanda, sobras e compras.

## Regra principal
Trabalhe SOMENTE na tarefa solicitada. Não implemente melhorias fora do escopo.

## Antes de alterar código
1. Leia `docs/DEVELOPMENT_STATUS.md`.
2. Leia somente a documentação necessária para a tarefa:
   - regras de negócio: `docs/BUSINESS_RULES.md`
   - arquitetura: `docs/ARCHITECTURE.md`
   - escopo do produto: `docs/PROJECT_SPEC.md`
3. Identifique os arquivos diretamente relacionados à tarefa.
4. Reutilize componentes, funções, serviços, tipos e padrões já existentes.

## Durante a implementação
- Não refatore áreas não relacionadas.
- Não renomeie arquivos, componentes ou funções sem necessidade.
- Não atualize dependências sem necessidade explícita.
- Não altere banco, schema ou arquitetura global sem justificativa ligada à tarefa.
- Evite duplicação.
- Preserve funcionalidades já concluídas.
- Faça alterações pequenas e verificáveis.
- Não introduza funcionalidades futuras apenas porque parecem úteis.

## Testes
- Execute primeiro testes focados no módulo alterado.
- Execute lint/typecheck do escopo quando aplicável.
- Só rode a suíte completa quando a alteração justificar.
- Não declare sucesso sem informar o que foi realmente testado.

## Saúde e segurança
Este sistema auxilia processos operacionais e farmacêuticos. Regras clínicas, doses, estabilidade, compatibilidade, diluição ou decisão terapêutica não devem ser inventadas pelo código ou pelo agente. Quando uma regra depender de referência clínica, mantenha-a configurável, rastreável e validável por profissional autorizado.

## Ao concluir uma tarefa
Atualize `docs/DEVELOPMENT_STATUS.md` apenas com:
- o que ficou concluído;
- pendências novas;
- decisão técnica relevante e duradoura.

## Resposta final
Seja curto. Informe apenas:
1. o que foi implementado;
2. arquivos alterados;
3. testes executados e resultado;
4. pendências ou riscos reais.

## Fora do escopo
Se descobrir algo importante fora da tarefa:
- não implemente;
- registre como sugestão de nova Issue.
