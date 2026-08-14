---
name: oncologia-quantitativo-previsao
description: Implementar e revisar quantitativo e previsão de demanda da Oncologia Cacoal. Usar em cálculo por período, cobertura, reservas, déficit, memória de cálculo e recálculo.
---

# Quantitativo e previsão

Aplicar o Modo de Economia de Tokens: ler somente os arquivos diretamente relacionados, reutilizar serviços e padrões existentes, testar primeiro o fluxo alterado e evitar refatoração fora do escopo.

## Contexto obrigatório

- Ler a linha deste módulo em `docs/REFERENCIAS_VISUAIS_E_ORQUESTRACAO.md`.
- Usar `docs/referencias-visuais/5.png` como referência visual, sem transformar a imagem na interface.
- Preservar dados fictícios, menor privilégio, auditoria e revisão humana.
- Consultar como lentes especializadas: motor-previsao-demanda, doses-apresentacoes, cenarios-risco-estoque, conciliacao-previsto-realizado, frontend-ux e qa-oncologia.

## Fluxo

1. Confirmar as funções do módulo: demanda, cobertura, reservas, déficit, premissas, recálculo e memória explicável.
2. Inspecionar modelos, serviços, formulários, rotas, templates e testes já existentes somente quando relacionados.
3. Implementar a menor mudança completa, mantendo regra de domínio fora da interface.
4. Exibir estados vazio, carregando, sucesso, erro, conflito e permissão negada quando aplicáveis.
5. Testar o caminho feliz, validações, autorização, idempotência e regressões do módulo.
6. Relatar alteração, arquivos, testes e pendências reais.

## Limites

Não inventar regra clínica, dose, estabilidade, protocolo ou prioridade. Não confirmar agenda, movimentar estoque, criar compra ou alterar acesso automaticamente quando a ação exigir profissional autorizado.
