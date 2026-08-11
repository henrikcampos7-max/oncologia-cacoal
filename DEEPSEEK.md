# DEEPSEEK.md — Projeto Oncologia Cacoal

## Objetivo
Desenvolver e manter o sistema de gestão oncológica com foco em segurança, rastreabilidade, estoque, agenda, previsão de demanda, sobras e compras.

## Regra principal
Trabalhe SOMENTE na tarefa solicitada. Não implemente melhorias fora do escopo.

## Antes de alterar código
1. Leia `docs/DEVELOPMENT_STATUS.md`.
2. Consulte apenas os documentos necessários: `docs/PROJECT_SPEC.md`, `docs/BUSINESS_RULES.md` e `docs/ARCHITECTURE.md`.
3. Identifique somente os arquivos diretamente relacionados à tarefa.
4. Reutilize código existente antes de criar componentes, serviços, funções, tipos ou dependências.

## Regras para economizar tokens
- Não analise o repositório inteiro sem necessidade.
- Não repita requisitos já documentados.
- Não reproduza arquivos completos se apenas parte deles precisa mudar.
- Não faça refatoração estética.
- Não proponha funcionalidades fora do escopo.
- Trabalhe em uma única Issue por vez.
- Prefira alteração mínima, testável e verificável.
- Mantenha a resposta final curta.

## Implementação
- Não refatore módulos não relacionados.
- Não renomeie arquivos sem necessidade.
- Não atualize dependências sem necessidade explícita.
- Não altere arquitetura global sem vínculo direto com a Issue.
- Preserve funcionalidades concluídas.
- Evite duplicação.
- Faça alterações pequenas e testáveis.

## Segurança clínica
Nunca invente doses, estabilidade, compatibilidade, diluição, concentração, via ou regras terapêuticas. Regras clínicas devem ser configuráveis, rastreáveis e sujeitas à validação profissional.

## Testes
- Execute testes focados no módulo alterado.
- Faça typecheck/lint quando aplicável.
- Só execute toda a suíte quando a mudança justificar.
- Não declare sucesso sem informar o que foi testado.

## Conclusão
Atualize `docs/DEVELOPMENT_STATUS.md` somente quando houver mudança real de status.

Resposta final:
1. Implementado
2. Arquivos alterados
3. Testes
4. Pendências/riscos
