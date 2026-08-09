# Revisão de Qualidade e Segurança — Arquitetura MVP Oncologia Cacoal

> **Escopo:** `docs/ARQUITETURA_MVP.md`, `README.md`, `SECURITY.md` e instruções do repositório.
> **Data:** 2026-08-09 | **Versão revisada:** ARQUITETURA_MVP.md v0.2 (rascunho)
> **Agente:** qualidade-seguranca
> **Aviso:** Esta revisão cobre somente documentação. Não declara conformidade legal, clínica ou regulatória.

---

## Sumário executivo

A documentação revisada demonstra intenção clara de adotar segurança e privacidade por desenho. Os princípios de pseudonimização, auditoria transacional, aprovação humana obrigatória e proibição de equivalência automática estão registrados e são consistentes com LGPD e boas práticas de sistemas de saúde. Nenhuma credencial, dado real ou PII foi encontrado nos documentos.

**Conclusão: Aprovado com ressalvas.**

O rascunho está adequado para prosseguir para decisão de stack e Fase 1, condicionado à resolução das pendências de alta gravidade listadas abaixo antes de qualquer implementação com dados reais.

---

## Achados por gravidade

### 🔴 Alta — Exige decisão ou mitigação antes de implementar

| # | Achado | Evidência | Correção recomendada |
|---|--------|-----------|----------------------|
| A01 | **Estratégia de pseudonimização indefinida (P06/D06):** O documento exige pseudonimização de pacientes antes de qualquer módulo com dados de tratamento, mas o mecanismo técnico, o responsável pelo de-para e o controle de acesso ao mapeamento não estão definidos. Sem isso, a Fase 1 não pode ser iniciada com segurança. | ARQUITETURA_MVP.md §1.3 P06, §3.1 Paciente, RC08 | Registrar ADR (Architecture Decision Record) definindo: mecanismo técnico (ex.: tabela separada criptografada com KMS, serviço isolado), responsável humano pelo de-para e política de acesso. Aprovar antes da Fase 1. |
| A02 | **Fluxo de aprovação de compras e movimentações não detalhado (P03/D04):** RC04 exige aprovação por perfil `aprovador`, mas não há definição de quem pode ser aprovador, quórum mínimo ou restrição de auto-aprovação (aprovador que também criou o rascunho). Risco de aprovação indevida. | ARQUITETURA_MVP.md §3.4 RC04, §1.3 P03 | Definir e documentar: quem pode ser designado aprovador, se auto-aprovação é proibida e se há exigência de dois aprovadores para valores acima de um limite. |
| A03 | **Auditoria sem menção a controle de integridade do log:** RC05 define que falha na auditoria reverte a transação, mas não há requisito de imutabilidade técnica (ex.: append-only, assinatura ou hash encadeado). Um atacante com acesso ao banco poderia alterar logs. | ARQUITETURA_MVP.md §3.4 RC05, entidade `Auditoria` | Adicionar requisito explícito de imutabilidade técnica: ex. tabela append-only sem UPDATE/DELETE, assinatura de hash ou exportação periódica para storage imutável. |
| A04 | **Controle de acesso ao de-para de pseudônimos ausente do modelo de dados:** A entidade `Paciente` não inclui qualquer referência ao sistema separado de mapeamento. Sem isso, o isolamento pode ser implementado incorretamente. | ARQUITETURA_MVP.md §3.1 Paciente | Documentar explicitamente que o serviço/tabela de de-para é separado, com controle de acesso independente, e que a API principal nunca retorna o mapeamento reverso. |

---

### 🟡 Média — Importante corrigir antes de entrar em homologação

| # | Achado | Evidência | Correção recomendada |
|---|--------|-----------|----------------------|
| M01 | **Prazo de alerta de validade dependente de confirmação (D02):** RC06 define 60 dias como sugestão, mas marca como pendente. Se o prazo real for menor (ex.: 30 dias), lotes podem vencer sem alerta oportuno, causando perda de medicamentos oncológicos caros. | ARQUITETURA_MVP.md §3.4 RC06 | Confirmar o prazo mínimo com o farmacêutico responsável e registrar como decisão fechada no ADR antes da implementação de alertas. |
| M02 | **Regra de ponto de reposição indefinida (P02/D03):** A sugestão de compra (R06) depende dessa regra. Com ela indefinida, o algoritmo pode gerar sugestões de compra erradas (excesso ou falta). | ARQUITETURA_MVP.md §1.3 P02 | Definir fórmula com responsável clínico-administrativo: cobertura em dias, quantidade fixa ou percentual do consumo médio. Documentar e testar. |
| M03 | **Ausência de critério de aceitação para importação de XLSX com erro parcial:** A Seção 5.1 menciona "rejeitar linhas inválidas com relatório de erros; não alterar estoque em importações com erro", mas não há critério claro do que constitui "erro" (linha, arquivo inteiro, lote de linhas). | ARQUITETURA_MVP.md §5.1 Importação | Definir: importação é atômica (tudo ou nada) ou admite sucesso parcial com relatório? Documentar critério de validação por linha. |
| M04 | **Perfil `admin` sem escopos definidos:** O modelo de dados lista três perfis (operador, aprovador, admin), mas somente operador e aprovador têm papéis descritos na documentação. O escopo exato de `admin` (pode criar usuários? Pode excluir registros auditados?) está omitido, criando risco de escalada de privilégio. | ARQUITETURA_MVP.md §3.1 Usuario | Documentar explicitamente as permissões do perfil `admin`, incluindo o que ele NÃO pode fazer (ex.: excluir registros de auditoria). |
| M05 | **Alerta de estoque negativo não mencionado:** RC01 proíbe saldo negativo, mas não há alerta dedicado para essa condição. Se o controle falhar, o sistema pode operar silenciosamente com saldo negativo. | ARQUITETURA_MVP.md §3.4 RC01, entidade `Alerta` | Adicionar tipo de alerta `estoque_negativo` e regra de que a movimentação de saída deve ser bloqueada — não só alertada — quando o disponível for zero. |

---

### 🔵 Baixa — Melhorias recomendadas

| # | Achado | Evidência | Correção recomendada |
|---|--------|-----------|----------------------|
| B01 | **Formato de exportação de relatórios indefinido (P04/D05):** Sem decisão, a implementação pode criar integrações externas não revisadas (ex.: e-mail automático de planilhas com dados de medicamentos). | ARQUITETURA_MVP.md §1.3 P04 | Definir destinos permitidos antes da Fase 4; excluir envio automático por e-mail sem aprovação humana. |
| B02 | **Aviso de limitação clínica previsto somente no frontend:** A Seção 6.2 menciona aviso visível na UI, mas não há requisito de que respostas da API também incluam metadado indicando caráter de apoio administrativo. | ARQUITETURA_MVP.md §6.2 frontend-ux | Considerar incluir campo `aviso_uso` em respostas de relatórios/sugestões de compra, reforçando que o valor é estimativa administrativa. |
| B03 | **Critério de "alerta duplicado" precisa de exemplo:** A seção de testes menciona "não duplicar alerta de condição ainda ativa", mas não há requisito formal de deduplicação. | ARQUITETURA_MVP.md §5.1 Alertas | Documentar regra de deduplicação: ex. um alerta aberto por (tipo, referencia_id) já existente não gera novo alerta até ser resolvido. |
| B04 | **SECURITY.md não cobre resposta a incidentes:** O arquivo define boas práticas de não incluir dados sensíveis, mas não orienta o que fazer se um dado real for descoberto em ambiente de teste/staging (além de "remover do histórico"). | SECURITY.md | Adicionar seção de resposta a incidentes: contato responsável, prazo de notificação interna e referência ao encarregado de dados (DPO) quando definido. |
| B05 | **Nenhuma referência a rate limiting, CSRF ou proteção de API:** Para um sistema multiusuário com dados de saúde, mesmo em intranet, esses controles são mínimos esperados. | ARQUITETURA_MVP.md geral | Adicionar requisitos mínimos de segurança de API ao documento após decisão de stack: autenticação stateless (ex. JWT com expiração curta), CSRF token em formulários, rate limiting em endpoints de autenticação. |

---

## Pontos positivos confirmados

- ✅ Nenhum dado real de paciente, credencial, planilha ou PII encontrado nos documentos.
- ✅ Pseudonimização exigida antes de qualquer módulo com dados de tratamento (R11, RC08).
- ✅ Reserva lógica claramente separada de movimentação física (Seção 3.1 e fórmula de disponível).
- ✅ Aprovação humana obrigatória para compras, movimentações e cadastros (R10, RC04).
- ✅ Precisão decimal e unidade explícita obrigatórias (R12, RC09).
- ✅ Equivalência e conversão entre apresentações explicitamente proibidas (R12, Medicamento).
- ✅ Auditoria transacional com reversão em caso de falha (RC05).
- ✅ Aviso clínico previsto na UI (Seção 6.2).
- ✅ FEFO implementado como regra crítica (RC02).
- ✅ Stack tecnológico não adotado sem decisão documentada (D01).
- ✅ Conformidade LGPD não declarada automaticamente (D08).

---

## Pendências que exigem decisão humana

As seguintes decisões estão bloqueadas para ação humana e **não podem ser resolvidas pelo agente**:

| # | Pendência | Gravidade | Responsável sugerido |
|---|-----------|-----------|----------------------|
| H01 | Definir mecanismo técnico e responsável pela pseudonimização de pacientes (D06/P06) | 🔴 Alta | Equipe técnica + DPO/jurídico |
| H02 | Definir quem pode ser aprovador e proibir auto-aprovação (P03/D04) | 🔴 Alta | Gestão administrativa |
| H03 | Definir imutabilidade técnica do log de auditoria | 🔴 Alta | Equipe técnica |
| H04 | Confirmar prazo de antecedência do alerta de validade (D02) | 🟡 Média | Farmacêutico responsável |
| H05 | Definir fórmula do ponto de reposição (P02/D03) | 🟡 Média | Farmacêutico/administrativo |
| H06 | Definir escopo exato do perfil `admin` | 🟡 Média | Equipe técnica + gestão |
| H07 | Confirmar se importação de XLSX é atômica ou admite sucesso parcial | 🟡 Média | Equipe técnica + operação |
| H08 | Definir destinos permitidos para exportação de relatórios (D05/P04) | 🔵 Baixa | Gestão + DPO |
| H09 | Escolha do stack tecnológico (D01) | Bloqueante | Equipe técnica |

---

## Conclusão

**Aprovado com ressalvas.**

O rascunho `ARQUITETURA_MVP.md v0.2` pode ser usado como base para discussão e decisão de stack, pois:
- não contém dados reais ou credenciais;
- estabelece controles corretos de privacidade, auditoria e aprovação humana;
- delimita o escopo clínico e proíbe decisões automáticas de equivalência.

A implementação de qualquer fase **fica condicionada** à resolução prévia dos achados A01, A02 e A03 (alta gravidade), especialmente a definição e aprovação da estratégia de pseudonimização (H01) antes de qualquer módulo que trate dados de tratamento de pacientes.

---

*Revisão conduzida pelo agente `qualidade-seguranca`. Não constitui auditoria de segurança formal, revisão jurídica, farmacêutica ou de conformidade regulatória.*
