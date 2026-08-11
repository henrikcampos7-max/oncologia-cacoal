# Agentes GitHub Copilot — Gestão Oncológica

Pacote com 24 agentes personalizados para o projeto de previsão de demanda, estoque, sobras e compras do Centro de Oncologia de Cacoal.

## Instalação

1. Abra o repositório do projeto no GitHub.
2. Na raiz do projeto, crie a pasta `.github/agents`.
3. Copie os arquivos `*.agent.md` deste pacote para essa pasta.
4. Copie `.github/copilot-instructions.md` para o mesmo caminho no repositório.
5. Faça commit das alterações na branch principal.
6. No GitHub Copilot, abra o seletor de agentes e escolha o agente adequado.

Estrutura esperada:

```text
seu-projeto/
└── .github/
    ├── copilot-instructions.md
    └── agents/
        ├── arquiteto-oncologia.agent.md
        ├── produto-requisitos.agent.md
        ├── banco-dados.agent.md
        ├── estoque-compras.agent.md
        ├── sobras-estabilidade.agent.md
        ├── implementador-fullstack.agent.md
        ├── backend-api.agent.md
        ├── frontend-ux.agent.md
        ├── perfis-acesso.agent.md
        ├── importacao-relatorios.agent.md
        ├── integracoes.agent.md
        ├── notificacoes.agent.md
        ├── protocolos-dados-clinicos.agent.md
        ├── agenda-oncologica.agent.md
        ├── planejamento-ciclos.agent.md
        ├── motor-previsao-demanda.agent.md
        ├── doses-apresentacoes.agent.md
        ├── cenarios-risco-estoque.agent.md
        ├── conciliacao-previsto-realizado.agent.md
        ├── planejamento-reposicao.agent.md
        ├── qa-oncologia.agent.md
        ├── seguranca-lgpd.agent.md
        ├── devops-implantacao.agent.md
        └── documentacao.agent.md
```

## Qual agente usar

| Agente | Use para |
| --- | --- |
| `arquiteto-oncologia` | Analisar pedidos grandes, dependências, banco de dados e criar plano antes da implementação |
| `produto-requisitos` | Transformar ideias operacionais em histórias, fluxos e critérios de aceite |
| `banco-dados` | Modelagem, migrações, integridade, índices e desempenho do banco |
| `estoque-compras` | Demanda mensal, estoque fechado, transferências, frascos e lista de compras |
| `sobras-estabilidade` | Sobra real/projetada, estabilidade, FEFO, reaproveitamento e rastreabilidade |
| `implementador-fullstack` | Implementar telas, APIs, banco, validações e integrações |
| `backend-api` | Serviços, regras transacionais, APIs, filas e idempotência |
| `frontend-ux` | Painéis, formulários, acessibilidade e experiência no celular/computador |
| `perfis-acesso` | Perfis, matriz de permissões e autorização por unidade |
| `importacao-relatorios` | Importar Excel, CSV ou PDF com validação e conciliação |
| `integracoes` | Integrações com GMED, agenda, estoque e serviços externos |
| `notificacoes` | Alertas na aplicação, Windows e canais institucionais aprovados |
| `protocolos-dados-clinicos` | Catálogo versionado de medicamentos, protocolos e regras farmacêuticas |
| `agenda-oncologica` | Interpretar agenda, status, início de tratamento e datas confirmadas |
| `planejamento-ciclos` | Projetar ciclos, dias de aplicação, intervalos e término previsto |
| `motor-previsao-demanda` | Consolidar demanda futura por medicamento, período e nível de confiança |
| `doses-apresentacoes` | Converter dose prevista em mg/UI/mL e apresentações necessárias |
| `cenarios-risco-estoque` | Comparar cenários confirmado, provável e potencial e identificar risco de falta |
| `conciliacao-previsto-realizado` | Comparar previsão com aplicação/consumo real e recalibrar o planejamento |
| `planejamento-reposicao` | Calcular quando e quanto comprar considerando saldo, pedidos e prazo do fornecedor |
| `qa-oncologia` | Testar cálculos, permissões, regressões e critérios de aceite |
| `seguranca-lgpd` | Revisar autenticação, perfis, auditoria, dados pessoais e vulnerabilidades |
| `devops-implantacao` | CI/CD, ambientes, backups, monitoramento e publicação segura |
| `documentacao` | Manuais técnicos, operacionais, changelog e documentação de API |

## Fluxo recomendado

1. Peça ao `arquiteto-oncologia` para analisar a solicitação e criar o plano.
2. Use o especialista do domínio: `estoque-compras` ou `sobras-estabilidade`.
3. Escolha um especialista técnico: banco, backend, frontend, importação, integração ou notificações.
4. Para previsão, siga: `agenda-oncologica` → `planejamento-ciclos` → `doses-apresentacoes` → `motor-previsao-demanda` → `cenarios-risco-estoque` → `planejamento-reposicao`.
5. Envie o plano validado ao `implementador-fullstack` quando a mudança atravessar várias camadas.
6. Use o `qa-oncologia` e `conciliacao-previsto-realizado` para validar e acompanhar a precisão.
7. Antes de produção, use `seguranca-lgpd` e `devops-implantacao`.

## Exemplos de comandos

```text
Use o agente arquiteto-oncologia para analisar esta issue e criar um plano de implementação sem alterar o código.
```

```text
Use o agente estoque-compras para implementar o cálculo mensal por paciente e por medicamento, preservando os níveis separados de agregação.
```

```text
Use o agente sobras-estabilidade para implementar o fluxo: demanda bruta → sobras válidas → demanda líquida → estoque → compra, com FEFO e rastreabilidade.
```

```text
Use o agente qa-oncologia para testar a alteração desta pull request, incluindo arredondamento de frascos, estoque insuficiente, transferências e concorrência.
```

```text
Use o agente planejamento-ciclos para projetar todas as ocorrências a partir da data de início, do número de ciclos e dos dias de aplicação do protocolo, sem criar agendamentos confirmados automaticamente.
```

```text
Use o agente motor-previsao-demanda para consolidar as ocorrências confirmadas e projetadas dos próximos 90 dias por medicamento e por mês, mantendo separado o nível de confiança.
```

## Regra essencial

Os agentes auxiliam no desenvolvimento do software. Eles não devem tomar decisões clínicas autônomas, prescrever tratamentos nem transformar dados incompletos em regras assistenciais. Toda regra clínica ou farmacêutica precisa de fonte, versionamento e aprovação humana antes de entrar em produção.
