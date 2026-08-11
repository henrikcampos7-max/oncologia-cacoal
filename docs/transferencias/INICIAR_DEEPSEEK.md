# COMANDO CURTO PARA INICIAR NO DEEPSEEK

Leia nesta ordem:
1. `PROMPT_MESTRE_TRANSFERENCIAS.md`
2. `AGENTS_TRANSFERENCIAS.md`
3. `SKILLS_TRANSFERENCIAS.md`

Depois analise integralmente o repositório atual antes de alterar qualquer arquivo.

Primeira tarefa:
- mapear stack, banco, auth, módulo de estoque, previsão de compra, uploads, testes e UI;
- localizar os pontos de integração do novo módulo;
- apresentar um plano por arquivos;
- só então iniciar a Fase 1.

Regras:
- não reescrever o projeto;
- preservar funções existentes;
- usar migrações seguras;
- IA nunca aprova entrada de estoque;
- aprovação farmacêutica é obrigatória;
- toda entrada em estoque precisa ser atômica e idempotente;
- transferências em trânsito não são saldo físico;
- lote e validade devem permanecer separados;
- alterações devem vir acompanhadas de testes.
