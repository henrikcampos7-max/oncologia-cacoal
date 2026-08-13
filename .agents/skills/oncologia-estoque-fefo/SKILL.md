---
name: oncologia-estoque-fefo
description: Implementar e revisar estoque, lotes, reservas, validade e FEFO na Oncologia Cacoal. Usar em entradas, saídas, ajustes, bloqueios, cobertura e fila FEFO.
---

# Estoque e FEFO

Aplicar o Modo de Economia de Tokens: ler somente os arquivos diretamente relacionados, reutilizar serviços e padrões existentes, testar primeiro o fluxo alterado e evitar refatoração fora do escopo.

## Contexto obrigatório

- Ler a linha deste módulo em `docs/REFERENCIAS_VISUAIS_E_ORQUESTRACAO.md`.
- Usar `docs/referencias-visuais/7.png` como referência visual, sem transformar a imagem na interface.
- Preservar dados fictícios, menor privilégio, auditoria e revisão humana.
- Consultar como lentes especializadas: backend-estoque, estoque-compras, sobras-estabilidade, banco-dados, seguranca-lgpd e qa-oncologia.

## Fluxo

1. Confirmar as funções do módulo: lotes, entrada, movimentação, reserva, bloqueio, validade, cobertura e FEFO.
2. Inspecionar modelos, serviços, formulários, rotas, templates e testes já existentes somente quando relacionados.
3. Implementar a menor mudança completa, mantendo regra de domínio fora da interface.
4. Exibir estados vazio, carregando, sucesso, erro, conflito e permissão negada quando aplicáveis.
5. Testar o caminho feliz, validações, autorização, idempotência e regressões do módulo.
6. Relatar alteração, arquivos, testes e pendências reais.

## Limites

Não inventar regra clínica, dose, estabilidade, protocolo ou prioridade. Não confirmar agenda, movimentar estoque, criar compra ou alterar acesso automaticamente quando a ação exigir profissional autorizado.
