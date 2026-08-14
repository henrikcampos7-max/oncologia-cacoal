# Referências visuais e orquestração

As imagens em `docs/referencias-visuais/` são especificações visuais com dados fictícios. Implementar componentes reais e acessíveis; não exibir a imagem como substituta da funcionalidade.

## Modo de Economia de Tokens

1. Selecionar a linha do módulo solicitado.
2. Ler a skill e apenas os especialistas necessários para a mudança.
3. Inspecionar somente arquivos relacionados.
4. Executar testes focados; ampliar apenas quando a alteração justificar.
5. Responder com alteração, arquivos, testes e pendências.

## Matriz

| Referência | Módulo | Skill | Orquestrador | Especialistas complementares |
| --- | --- | --- | --- | --- |
| `acesso.png` | Acesso seguro | `oncologia-acesso-seguro` | `modulo-acesso-seguro` | perfis-acesso; seguranca-lgpd; frontend-ux; qa-oncologia; qualidade-seguranca |
| `1.png` | Painel farmacêutico | `oncologia-painel-farmaceutico` | `modulo-painel-farmaceutico` | produto-requisitos; frontend-ux; motor-previsao-demanda; estoque-compras; qa-oncologia |
| `2.png` | Agenda e validações | `oncologia-agenda-validacoes` | `modulo-agenda-validacoes` | agenda-oncologica; protocolos-dados-clinicos; planejamento-ciclos; frontend-ux; qa-oncologia |
| `3.png` | Pacientes e protocolos | `oncologia-pacientes-protocolos` | `modulo-pacientes-protocolos` | protocolos-dados-clinicos; planejamento-ciclos; perfis-acesso; frontend-ux; seguranca-lgpd; qa-oncologia |
| `3.1.png` | Medicações orais | `oncologia-medicacoes-orais` | `modulo-medicacoes-orais` | agenda-oncologica; protocolos-dados-clinicos; planejamento-ciclos; planejamento-reposicao; frontend-ux; qa-oncologia |
| `4.png` | Medicamentos e apresentações | `oncologia-medicamentos-apresentacoes` | `modulo-medicamentos-apresentacoes` | doses-apresentacoes; banco-dados; estoque-compras; protocolos-dados-clinicos; frontend-ux; qa-oncologia |
| `5.png` | Quantitativo e previsão | `oncologia-quantitativo-previsao` | `modulo-quantitativo-previsao` | motor-previsao-demanda; doses-apresentacoes; cenarios-risco-estoque; conciliacao-previsto-realizado; frontend-ux; qa-oncologia |
| `6.png` | Central de alertas | `oncologia-central-alertas` | `modulo-central-alertas` | notificacoes; cenarios-risco-estoque; agenda-oncologica; estoque-compras; frontend-ux; qa-oncologia |
| `7.png` | Estoque e FEFO | `oncologia-estoque-fefo` | `modulo-estoque-fefo` | backend-estoque; estoque-compras; sobras-estabilidade; banco-dados; seguranca-lgpd; qa-oncologia |
| `8.png` | Planejamento de compras | `oncologia-planejamento-compras` | `modulo-planejamento-compras` | planejamento-reposicao; estoque-compras; motor-previsao-demanda; perfis-acesso; frontend-ux; qa-oncologia |
| `10.png` | Auditoria e histórico | `oncologia-auditoria-historico` | `modulo-auditoria-historico` | seguranca-lgpd; perfis-acesso; backend-api; qualidade-seguranca; documentacao; qa-oncologia |
| `11.png` | Relatórios e indicadores | `oncologia-relatorios-indicadores` | `modulo-relatorios-indicadores` | conciliacao-previsto-realizado; importacao-relatorios; motor-previsao-demanda; frontend-ux; documentacao; qa-oncologia |
| `12.png` | Configurações do sistema | `oncologia-configuracoes-sistema` | `modulo-configuracoes-sistema` | perfis-acesso; seguranca-lgpd; devops-implantacao; notificacoes; frontend-ux; qa-oncologia |

## Barreiras obrigatórias

- Usar dados sintéticos em testes, exemplos, screenshots e logs.
- Não inventar regra clínica, dose, estabilidade, protocolo ou prioridade.
- Exigir confirmação humana para validação farmacêutica, movimentação crítica, compra e alteração de acesso.
- Manter cálculos explicáveis e regras de domínio fora da interface.
- Registrar operações sensíveis em trilha auditável e respeitar menor privilégio.
- Tratar exportações e backups como possíveis portadores de dados sensíveis.

## Ausência de imagem 9

A pasta fornecida não contém `9.png`. A cobertura inclui todas as 13 imagens efetivamente recebidas: acesso, `1.png` a `8.png` (incluindo `3.1.png`) e `10.png` a `12.png`.

## Implementação funcional

As referências foram ligadas às rotas Django reais. O backend existente cobre painel, agenda, pacientes, medicamentos, quantitativo, alertas, estoque, compras, auditoria e relatórios. Esta entrega acrescenta medicações orais, configurações por clínica, filtros reais, exportações e cópia sem credenciais. Imagens permanecem somente como especificação em `docs/referencias-visuais/`.
