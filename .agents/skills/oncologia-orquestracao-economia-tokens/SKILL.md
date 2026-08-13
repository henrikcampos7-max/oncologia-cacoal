---
name: oncologia-orquestracao-economia-tokens
description: Orquestrar mudanças modulares da Oncologia Cacoal em Modo de Economia de Tokens. Usar para selecionar a skill, os agentes especialistas, os arquivos e os testes mínimos necessários para uma tarefa.
---

# Orquestração com economia de tokens

Aplicar as regras permanentes do repositório e o Modo de Economia de Tokens.

## Fluxo

1. Ler `docs/REFERENCIAS_VISUAIS_E_ORQUESTRACAO.md` e selecionar somente a linha do módulo solicitado.
2. Carregar a skill do módulo e no máximo os especialistas necessários para produto, domínio, UX, QA ou segurança.
3. Inspecionar arquivos diretamente relacionados; evitar varredura ampla e refatoração adjacente.
4. Fazer uma mudança completa e verificável.
5. Rodar testes focados e ampliar somente se o risco justificar.
6. Responder apenas com alteração, arquivos, testes e pendências.

## Saída

Informar somente alteração, arquivos, testes executados e pendências ou riscos reais.
