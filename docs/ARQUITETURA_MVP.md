# Arquitetura inicial e modelo de dados — MVP Oncologia Cacoal

> **Status:** rascunho — requer aprovação humana antes de qualquer implementação.
> Nenhuma tecnologia foi adotada; todas as decisões técnicas marcadas com ⚠️ aguardam validação.
>
> **Privacidade e segurança:** este documento adota segurança e privacidade por desenho como requisitos de projeto. Os princípios de minimização de dados, pseudonimização e limitação de finalidade da LGPD guiam as decisões de modelagem. Conformidade legal não é declarada automaticamente — requer revisão jurídica e operacional.

---

## 1. Requisitos, suposições e pendências

### 1.1 Requisitos confirmados

| # | Requisito |
|---|-----------|
| R01 | Importar e validar dados da planilha de previsão mensal (XLSX), sem substituir o Excel na fase atual. |
| R02 | Manter cadastro de tratamentos por paciente (plano, medicamento, início, ciclos, dose, intervalo, status). |
| R03 | Calcular previsão mensal de consumo por medicamento a partir dos ciclos ativos. |
| R04 | Controlar estoque com saldo atual, entradas, saídas, lotes e datas de validade. |
| R05 | Gerar reservas de estoque com base na previsão; reservas são lógicas e não geram movimentação física. |
| R06 | Sugerir quantidades de compra quando estoque disponível (físico − reservas ativas) ficar abaixo do ponto de reposição. |
| R07 | Emitir alertas de medicamentos próximos ao vencimento, abaixo do estoque mínimo ou com reservas não atendidas. |
| R08 | Registrar auditoria de toda alteração com usuário, data/hora e valor anterior. |
| R09 | Gerar relatórios de consumo, estoque e compras, exportáveis. |
| R10 | Exigir revisão e aprovação humana para compras, movimentações e cadastros. |
| R11 | Adotar segurança e privacidade por desenho: autenticação, autorização e pseudonimização de pacientes devem ser implementadas antes de qualquer módulo que trate dados de tratamentos. |
| R12 | Quantidades de medicamentos devem ser armazenadas com precisão decimal e unidade explícita. Conversão ou equivalência entre medicamentos e apresentações é proibida sem validação farmacêutica humana. |

### 1.2 Suposições (precisam de confirmação)

| Cód | Suposição |
|-----|-----------|
| S01 | Cada paciente pode ter mais de um tratamento ativo simultaneamente. |
| S02 | O medicamento é identificado pelo nome + apresentação (ex. fictício: "Medicamento-X 500 mg/10 mL"). Nomes comerciais reais não são usados em exemplos. |
| S03 | O estoque é gerenciado por lote; múltiplos lotes de um mesmo medicamento podem coexistir. |
| S04 | O consumo do estoque segue FEFO (primeiro a vencer, primeiro a sair). |
| S05 | O sistema será multiusuário com pelo menos dois perfis: operador e aprovador. |
| S06 | A importação de XLSX é pontual e manual, não automática. |
| S07 | A moeda de compra é o Real (BRL). |

### 1.3 Pendências e lacunas

| Cód | Pendência | Impacto se não resolvida |
|-----|-----------|--------------------------|
| P01 | Definição do stack tecnológico (ver Seção 4). | Bloqueante para iniciar implementação. |
| P02 | Regra exata para "ponto de reposição": dias de cobertura, quantidade fixa ou percentual? | Pode gerar sugestões de compra incorretas. |
| P03 | Quem pode aprovar compras e movimentações? Existe fluxo de aprovação multinível? | Necessário para design de controle de acesso. |
| P04 | Formato e destino dos relatórios exportados (PDF, XLSX, e-mail, drive)? | Afeta integrações externas. |
| P05 | Há necessidade de acesso offline ou funciona somente em rede local/intranet? | Afeta decisão de implantação. |
| P06 | Estratégia de pseudonimização de pacientes: mecanismo técnico, responsável pelo de-para e controle de acesso ao mapeamento. | Obrigatório antes de qualquer implantação com dados reais. |

---

## 2. Limites dos módulos

```
┌──────────────┐   ┌──────────────────┐   ┌─────────────────┐
│   Agenda e   │──▶│  Medicamentos e  │──▶│    Estoque,     │
│ Tratamentos  │   │  Apresentações   │   │  Lotes e Validade│
└──────────────┘   └──────────────────┘   └────────┬────────┘
                                                    │
                          ┌─────────────────────────▼──────┐
                          │       Reservas e Compras        │
                          └─────────────────────────────────┘
                                          │
              ┌───────────────────────────▼───────────────────────────┐
              │                  Alertas e Relatórios                  │
              └───────────────────────────────────────────────────────┘
                                          │
              ┌───────────────────────────▼───────────────────────────┐
              │                       Auditoria                        │
              └───────────────────────────────────────────────────────┘
```

| Módulo | Responsabilidade | Fora do escopo |
|--------|-----------------|----------------|
| **Agenda e Tratamentos** | Cadastro de pacientes (pseudonimizados), planos, ciclos, datas, status. Cálculo de previsão mensal. | Prescrição médica, ajuste de dose. |
| **Medicamentos e Apresentações** | Cadastro de nome, apresentação, unidade, estoque mínimo, ponto de reposição. | Equivalência terapêutica, substituição. |
| **Estoque, Lotes e Validade** | Saldo por lote, data de validade, movimentações (entrada, saída, ajuste, descarte). Aplicação de FEFO. | Gestão de fornecedores, contratos. |
| **Reservas** | Criação e cancelamento de reservas de estoque baseadas na previsão de consumo. | Confirmação automática de aplicação. |
| **Compras** | Sugestão de quantidade a comprar. Registro de pedidos em rascunho. Aprovação humana obrigatória. | Emissão de ordem de compra, pagamento. |
| **Alertas** | Notificação de validade próxima, estoque baixo, reserva não atendida, compra pendente. | Integração com sistemas de notificação externos. |
| **Auditoria** | Log imutável de toda criação, alteração e exclusão com usuário, módulo e valores anterior/posterior. | Análise forense ou compliance regulatório. |
| **Relatórios** | Consumo mensal, estoque atual, previsão por período, sugestões de compra. Export para XLSX/PDF. | BI avançado, dashboards em tempo real. |

---

## 3. Modelo conceitual de dados

> Notação simplificada. Os tipos de dado são intencionais e não dependem do banco escolhido.

### 3.1 Entidades e atributos principais

> Minimização de dados: somente campos com requisito aprovado são incluídos no MVP. PII não prevista neste escopo.

```
Paciente
  id, codigo_pseudonimo, plano_saude, ativo
  (o de-para codigo_pseudonimo ↔ identidade real fica em sistema separado,
   com controle de acesso restrito; nenhum PII trafega neste sistema)

Tratamento
  id, paciente_id, medicamento_id, data_inicio, intervalo_dias,
  dose_por_ciclo DECIMAL, unidade VARCHAR, qtd_ciclos_previstos INTEGER,
  aplicacoes_por_ciclo INTEGER,
  status (ativo | suspenso | encerrado), observacoes

Medicamento
  id, nome VARCHAR, apresentacao VARCHAR, unidade_padrao VARCHAR,
  estoque_minimo DECIMAL, ponto_reposicao DECIMAL, ativo
  (unidade explícita e obrigatória; conversão entre apresentações
   é proibida sem validação farmacêutica humana)

Lote
  id, medicamento_id, numero_lote, data_validade DATE,
  quantidade_inicial DECIMAL, quantidade_atual DECIMAL,
  data_entrada DATE, nota_fiscal VARCHAR (opcional)

Movimentacao
  id, lote_id, tipo (entrada | saida | ajuste | descarte),
  quantidade DECIMAL, unidade VARCHAR, referencia_id (compra ou tratamento),
  usuario_id, data_hora, observacoes
  (reserva NÃO é movimentação física; ver cálculo de disponível abaixo)

Reserva
  id, tratamento_id, medicamento_id, mes_ano, quantidade_reservada DECIMAL,
  unidade VARCHAR, quantidade_atendida DECIMAL,
  status (aberta | parcial | atendida | cancelada)

Compra
  id, medicamento_id, quantidade_sugerida DECIMAL, quantidade_aprovada DECIMAL,
  unidade VARCHAR,
  status (rascunho | em_aprovacao | aprovada | recusada | recebida),
  aprovador_id (nulo até aprovação), data_criacao, data_aprovacao,
  observacoes

Alerta
  id, tipo (validade | estoque_baixo | reserva_nao_atendida | compra_pendente),
  referencia_tipo, referencia_id, mensagem,
  status (aberto | reconhecido | resolvido), data_hora

Auditoria
  id, tabela, registro_id, operacao (create | update | delete),
  usuario_id, data_hora, valor_anterior (JSON), valor_novo (JSON)

Usuario
  id, nome, email, perfil (operador | aprovador | admin), ativo
```

**Cálculo de disponível:**
```
disponivel(medicamento_id) =
    SUM(lote.quantidade_atual) WHERE medicamento_id = X
  − SUM(reserva.quantidade_reservada - reserva.quantidade_atendida)
      WHERE medicamento_id = X AND status IN (aberta, parcial)
```
Reservas reduzem o saldo disponível mas não criam movimentação física. Somente `entrada` (recebimento) e `saida` (consumo confirmado) geram `Movimentacao`.

### 3.2 Relacionamentos

```
Paciente ──< Tratamento >── Medicamento
Medicamento ──< Lote
Lote ──< Movimentacao
Tratamento ──< Reserva >── Medicamento
Compra >── Medicamento
Compra ──> Usuario (aprovador)
Movimentacao >── Usuario
Auditoria >── Usuario
```

### 3.3 Estados críticos

#### Tratamento
```
rascunho → ativo → suspenso ↔ ativo → encerrado
```

#### Reserva
```
aberta → parcial → atendida
       → cancelada
```

#### Compra
```
rascunho → em_aprovacao → aprovada → recebida
                        → recusada
```

### 3.4 Regras críticas

| Cód | Regra | Módulo |
|-----|-------|--------|
| RC01 | Nunca subtrair do estoque sem criar `Movimentacao` do tipo `saida` correspondente. | Estoque |
| RC02 | Ao sair estoque, consumir lote com menor `data_validade` primeiro (FEFO). | Estoque |
| RC03 | Reserva não pode ser criada para quantidade maior que `disponivel(medicamento_id)` (ver fórmula na Seção 3.1). | Reservas |
| RC04 | Compra só muda para "aprovada" mediante ação explícita de usuário com perfil aprovador. | Compras |
| RC05 | Auditoria é gravada em toda operação de escrita; falha na auditoria cancela a transação. | Auditoria |
| RC06 | Alerta de validade deve ser emitido com pelo menos 60 dias de antecedência. ⚠️ Prazo sujeito a confirmação (D02). | Alertas |
| RC07 | Medicamento com `disponivel` ≤ `estoque_minimo` gera alerta imediato; alerta não é duplicado enquanto a condição persistir. | Alertas |
| RC08 | Pacientes são identificados somente por `codigo_pseudonimo` neste sistema; o de-para fica em sistema separado com acesso restrito. Requer definição de P06. | Agenda |
| RC09 | Quantidades e doses são armazenadas com precisão decimal e unidade explícita; o sistema nunca converte automaticamente entre medicamentos ou apresentações distintas. | Medicamentos |
| RC10 | Alertas possuem estados (`aberto`, `reconhecido`, `resolvido`); reconhecer não resolve — o alerta só é resolvido quando a condição que o originou deixa de existir. Não gerar alerta duplicado para o mesmo tipo, referência e condição ainda ativa. | Alertas |

---

## 4. Opções de arquitetura e tecnologia

> ⚠️ Nenhuma opção foi adotada. Decisão requer aprovação humana antes de qualquer implementação.

### 4.1 Opção A — Aplicação web (SPA + API REST)

| Aspecto | Detalhe |
|---------|---------|
| Frontend | React, Vue ou Svelte |
| Backend | Node.js/Express, Django ou FastAPI |
| Banco | PostgreSQL |
| Autenticação | JWT com refresh token |
| Hospedagem | Servidor local ou VPS simples |
| **Vantagens** | Separação clara de camadas, escalável, ecossistema maduro. |
| **Riscos** | Maior complexidade inicial; exige manutenção de dois projetos. |
| **Recomendação** | Adequado se houver equipe com experiência web. |

### 4.2 Opção B — Aplicação fullstack integrada

| Aspecto | Detalhe |
|---------|---------|
| Stack | Next.js (React + API Routes) ou SvelteKit |
| Banco | PostgreSQL ou SQLite (início) |
| ORM | Prisma ou Drizzle |
| Autenticação | NextAuth / Lucia |
| **Vantagens** | Um repositório, menos configuração, deploy mais simples. |
| **Riscos** | Acoplamento entre UI e regras de negócio se não disciplinado. |
| **Recomendação** | Adequado para MVP rápido com equipe pequena. |

### 4.3 Opção C — Planilha evoluída com back-office simples

| Aspecto | Detalhe |
|---------|---------|
| Stack | Google Sheets / AppSheet ou Power Apps |
| **Vantagens** | Nenhuma implantação; equipe já familiarizada com Excel. |
| **Riscos** | Limitações de auditoria, controle de acesso e escalabilidade. Dependência de fornecedor SaaS. |
| **Recomendação** | Somente como solução transitória de curto prazo. |

### 4.4 Critérios de decisão recomendados

1. Experiência técnica da equipe mantenedora.
2. Disponibilidade de infraestrutura (servidor local vs. nuvem).
3. Prazo para o primeiro uso operacional.
4. Requisito de operação offline (P05).
5. Orçamento de manutenção de longo prazo.

---

## 5. Critérios de aceitação e sequência de implementação

### 5.1 Critérios gerais de aceitação

- Toda movimentação de estoque é rastreável até o usuário e o momento da ação.
- Nenhuma compra é registrada como "aprovada" sem ação explícita de aprovador.
- Dados fictícios são usados em todos os ambientes não-produção.
- Nenhum dado real de paciente trafega fora do ambiente controlado.
- O sistema exibe aviso visível de que não substitui avaliação clínica ou farmacêutica.

### 5.2 Testes necessários por módulo

| Módulo | Testes mínimos |
|--------|---------------|
| Autenticação/Autorização | Acesso negado sem autenticação; perfil operador não pode aprovar compras. |
| Estoque | FEFO correto; não permitir saldo negativo; auditoria em toda movimentação; unidade explícita e sem conversão automática. |
| Reservas | Não reservar além do disponível (físico − reservas ativas); cancelamento libera saldo disponível. |
| Compras | Fluxo de aprovação; rascunho não afeta estoque; aprovação só por perfil correto. |
| Alertas | Alerta disparado no prazo correto; reconhecer não resolve; não duplicar alerta de condição ainda ativa. |
| Auditoria | Falha na gravação de auditoria reverte a operação; log é imutável. |
| Importação | Rejeitar linhas inválidas com relatório de erros; não alterar estoque em importações com erro. |

### 5.3 Sequência de implementação sugerida

```
Fase 1 — Base e controles fundamentais (sem UI)
  1.1  Modelo de dados e migrações
  1.2  Autenticação e autorização (perfis: operador, aprovador, admin)
  1.3  Auditoria transacional (RC05) — deve preceder qualquer escrita de dados
  1.4  Pseudonimização de pacientes (RC08, P06) — obrigatória antes do módulo de tratamentos
  1.5  Cadastro de medicamentos (com unidade e precisão decimal obrigatórias — RC09)
  1.6  Cadastro e movimentação de lotes (entrada/saída/ajuste/descarte com FEFO — RC01, RC02)
  1.7  Testes unitários de regras críticas RC01–RC10

Fase 2 — Agenda e previsão
  2.1  Cadastro de tratamentos (pacientes pseudonimizados)
  2.2  Cálculo de previsão mensal de consumo
  2.3  Geração de reservas a partir da previsão (com fórmula de disponível — RC03)
  2.4  Testes de reservas

Fase 3 — Compras e alertas
  3.1  Sugestão de compra (baseada em disponível, não em físico bruto)
  3.2  Fluxo de aprovação (RC04)
  3.3  Motor de alertas com estados aberto/reconhecido/resolvido (RC06, RC07, RC10)
  3.4  Testes de alertas e compras

Fase 4 — Interface e relatórios
  4.1  UI de consulta e cadastro
  4.2  Relatórios e exportação
  4.3  Importação de XLSX

Fase 5 — Revisão e implantação
  5.1  Revisão de segurança e pentest básico
  5.2  Homologação com responsáveis humanos
```

---

## 6. Divisão de próximas tarefas

### 6.1 Equipe backend-estoque

- [ ] Decidir stack (Seção 4) e registrar ADR (Architecture Decision Record).
- [ ] Criar modelo de dados conforme Seção 3 com migrações versionadas.
- [ ] Implementar autenticação e autorização na Fase 1 (antes de qualquer módulo de tratamentos).
- [ ] Implementar auditoria transacional na Fase 1 (RC05).
- [ ] Implementar pseudonimização de pacientes na Fase 1 (RC08, P06).
- [ ] Implementar serviço de movimentação de estoque com FEFO e unidade explícita (RC01, RC02, RC09).
- [ ] Implementar cálculo de previsão mensal de consumo.
- [ ] Implementar serviço de reservas com validação de disponível (RC03).
- [ ] Implementar sugestão de compra e fluxo de aprovação (RC04).
- [ ] Implementar motor de alertas com estados aberto/reconhecido/resolvido (RC10).
- [ ] Criar suite de testes unitários para regras críticas RC01–RC10.

### 6.2 Equipe frontend-ux

- [ ] Aguardar decisão de stack (bloqueia início).
- [ ] Definir mapa de telas e fluxo de navegação.
- [ ] Prototipar telas de estoque, reservas e compras (sem dados reais).
- [ ] Implementar UI de alertas com distinção visual por nível de urgência.
- [ ] Implementar telas de relatórios com filtros por período e medicamento.
- [ ] Garantir aviso visível de que o sistema não substitui avaliação clínica.

### 6.3 Equipe qualidade-seguranca

- [ ] Revisar e aprovar modelo de dados desta documentação antes da implementação.
- [ ] Definir e aprovar estratégia de pseudonimização de pacientes (P06) antes da Fase 1.
- [ ] Validar regras de controle de acesso (P03).
- [ ] Criar plano de testes de integração e aceitação (incluindo testes de autenticação e auditoria).
- [ ] Revisar SECURITY.md após decisão de stack.
- [ ] Aprovar dados fictícios de teste antes de qualquer carga em ambiente.
- [ ] Conduzir revisão de segurança e privacidade antes da Fase 5.
- [ ] Validar conformidade com princípios da LGPD com responsável jurídico (não declarar conformidade automaticamente).

---

## Decisões que aguardam aprovação humana

| # | Decisão | Seção |
|---|---------|-------|
| D01 | Escolha do stack tecnológico (Opções A, B ou C) — nenhuma implementada. | 4 |
| D02 | Prazo de antecedência para alerta de validade (sugestão: 60 dias). | RC06 |
| D03 | Regra exata para ponto de reposição e cálculo de quantidade a comprar. | P02 |
| D04 | Fluxo de aprovação de compras (um nível ou multinível). | P03 |
| D05 | Formato e destino dos relatórios exportados. | P04 |
| D06 | Mecanismo técnico e responsável pela pseudonimização de pacientes. | P06, RC08 |
| D07 | Operação offline ou somente em rede (afeta implantação). | P05 |
| D08 | Conformidade regulatória LGPD — requer revisão jurídica; não declarada automaticamente. | R11 |

---

*Documento gerado em 2026-08-09. Versão 0.2 — rascunho para revisão humana.*
