# Instruções do repositório Oncologia Cacoal

## Objetivo e idioma

- Responda e documente em português do Brasil.
- Este projeto é um MVP de apoio administrativo para previsão de demanda, estoque e compras de medicamentos oncológicos.
- O sistema não substitui avaliação médica, farmacêutica, regulatória ou operacional humana.

## Modo economia de tokens

- Leia somente os arquivos diretamente relacionados à tarefa.
- Não repita instruções nem produza explicações extensas.
- Não invoque outros agentes, pesquisa web ou integrações externas sem solicitação explícita.
- Execute apenas testes relacionados às alterações.
- Ao concluir, informe somente: alteração, arquivos, testes e pendências.

## Dados e segurança

- Use exclusivamente dados fictícios em código, testes, exemplos e capturas de tela.
- Nunca adicione dados de pacientes, prescrições, carteirinhas, documentos, planilhas operacionais, bancos reais, segredos, tokens ou arquivos `.env`.
- Respeite `SECURITY.md` e `.gitignore`; não contorne suas exclusões.
- Não determine doses, protocolos, equivalência de medicamentos ou substituição de apresentações.
- Não aprove compras, movimentações de estoque, cadastros ou exclusões sem revisão humana.
- Mantenha rastreabilidade, auditoria, controle de acesso e validação explícita nas propostas técnicas.

## Desenvolvimento

- A arquitetura aprovada em 2026-08-09 é Django com páginas renderizadas no servidor e PostgreSQL. Não substitua framework, banco ou introduza serviço externo sem nova decisão documentada.
- Prefira alterações pequenas, reversíveis e limitadas ao escopo solicitado.
- Preserve a identidade visual existente; não redesenhe marcas com IA.
- Não modifique repositórios de terceiros.
- Não faça merge, implantação ou publicação automática.
- Use branch específica, commit objetivo e pull request em rascunho.
- Registre suposições e bloqueios; não invente requisitos ausentes.

## Qualidade

- Inclua critérios de aceitação e testes proporcionais ao risco.
- Trate cálculos de estoque, validade, reservas e compras como regras críticas.
- Mantenha validação humana antes de qualquer uso clínico ou operacional.
