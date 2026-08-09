# Recomendação Técnica Comparativa — MVP Oncologia Cacoal

> **Status:** Rascunho — aguardando aprovação humana. Nenhuma decisão aqui é definitiva.
> **Data:** 2026-08-09
> **Autor:** Agente planejador-arquitetura (revisão humana obrigatória antes de qualquer implementação)

---

## 1. Tabela Comparativa

| Critério | Opção A — Python/FastAPI + PostgreSQL | Opção B — Python/FastAPI + SQLite | Opção C — Node.js/Express + SQLite |
|---|---|---|---|
| **Instalação no Windows** | Moderada: requer Python, PostgreSQL e serviço de banco | Simples: Python + arquivo de banco embutido | Simples: Node.js + arquivo de banco embutido |
| **Atualização** | Moderada: migrações de esquema + reinicialização do serviço PostgreSQL | Simples: atualizar aplicação e executar migrações | Simples: atualizar aplicação e executar migrações |
| **Funcionamento local e rede interna** | Bom: PostgreSQL suporta múltiplas conexões simultâneas | Limitado: SQLite trava em escritas concorrentes; adequado para poucos usuários simultâneos | Limitado: mesmo comportamento do SQLite |
| **Consumo de memória** | Moderado: ~200–400 MB (app + PostgreSQL) | Baixo: ~80–150 MB (somente app) | Baixo: ~80–150 MB (somente app) |
| **Requisitos mínimos** | 4 GB RAM, 20 GB disco, Windows 10/11 | 2 GB RAM, 5 GB disco, Windows 10/11 | 2 GB RAM, 5 GB disco, Windows 10/11 |
| **Segurança e controle de acesso** | Alto: usuários de banco, roles, TLS opcional | Médio: controle na camada de aplicação; arquivo de banco precisa de permissões de SO | Médio: igual ao SQLite |
| **Backup e recuperação** | Robusto: `pg_dump`, PITR, replicação possível | Simples: copiar arquivo `.db`; sem PITR nativo | Simples: copiar arquivo `.db` |
| **Manutenção por equipe pequena** | Moderada: exige conhecimento de PostgreSQL | Alta: sem servidor adicional para manter | Alta: sem servidor adicional para manter |
| **Licenças e custos** | Gratuito (PostgreSQL licença PostgreSQL, Python MIT/PSF) | Gratuito (SQLite domínio público, Python MIT/PSF) | Gratuito (SQLite domínio público, Node.js MIT) |
| **Dependências externas** | Nenhuma obrigatória em nuvem | Nenhuma | Nenhuma |
| **Testes e migrações** | pytest + Alembic; banco de testes separado | pytest + Alembic ou SQLModel; banco em memória | Jest + Knex/Drizzle; banco em memória |
| **Evolução sem reescrita** | Alta: PostgreSQL escala bem; API REST reutilizável | Média: migração para PostgreSQL possível sem reescrever a API | Média: troca de banco possível; ecossistema JS pode divergir de ferramentas Python |
| **Importação XLSX atômica** | Sim: transação de banco garante atomicidade | Sim: transação SQLite garante atomicidade | Sim: transação SQLite garante atomicidade |
| **Auditoria e pseudonimização** | Facilitada: tabelas de log no PostgreSQL, particionamento | Possível: tabela de log no SQLite | Possível: tabela de log no SQLite |

---

## 2. Recomendação Principal e Alternativa de Contingência

### Recomendação principal — Opção A: Python/FastAPI + PostgreSQL

**Justificativa:**
- Suporte nativo a múltiplos usuários simultâneos na rede interna sem degradação de escrita.
- Controle de acesso granular no nível do banco de dados, além da camada de aplicação.
- Backup e recuperação robustos (`pg_dump` automatizado via Agendador de Tarefas do Windows).
- Alembic como ferramenta madura de migração de esquema com histórico auditável.
- Ecossistema Python amplamente documentado para equipes de saúde e dados.
- Evita reescrita prematura quando o volume de dados ou usuários crescer.

**Pré-condições para escolha:**
- Equipe ou responsável técnico capaz de instalar e manter PostgreSQL no Windows.
- Política de backup definida e testada antes de qualquer dado real.
- Aprovação do responsável pela segurança da informação.

### Alternativa de contingência — Opção B: Python/FastAPI + SQLite

**Justificativa:**
- Instalação e manutenção mais simples se a equipe não tiver perfil técnico para PostgreSQL.
- Adequada enquanto o número de usuários simultâneos for baixo (≤ 3 escritas concorrentes).
- Migração para PostgreSQL possível sem reescrever a API, desde que o ORM seja configurado de forma portável desde o início.
- Menor risco de falha de configuração na fase inicial.

**Limitações a monitorar:**
- Bloqueios de escrita em caso de importações XLSX simultâneas.
- Arquivo de banco precisa de permissões de SO restritas para evitar acesso não autorizado.
- Sem Point-in-Time Recovery nativo.

---

## 3. Arquitetura de Implantação Local e Rede Interna (linguagem simples)

```
Computadores da equipe (navegadores)
        │  HTTP na rede interna (porta ex.: 8000)
        ▼
  Servidor local (computador dedicado ou estação designada)
  ┌──────────────────────────────────────────────┐
  │  Aplicação Web (FastAPI / Python)            │
  │  - Servindo a interface HTML no navegador    │
  │  - Validando login e permissões              │
  │  - Processando importações XLSX              │
  │  - Gerando alertas e relatórios              │
  ├──────────────────────────────────────────────┤
  │  Banco de dados (PostgreSQL ou SQLite)       │
  │  - Armazena dados de medicamentos,           │
  │    lotes, movimentações e auditoria          │
  │  - Backup diário automatizado                │
  └──────────────────────────────────────────────┘
        │
        ▼
  Pasta de backup em rede (ou HD externo rotativo)
```

**Fluxo de acesso:**
1. Usuário abre o navegador em seu computador e acessa o endereço IP do servidor na rede interna.
2. A aplicação exige login com senha individual.
3. Cada ação fica registrada no log de auditoria.
4. Dados nunca saem da rede interna; sem dependência de internet para operação.

---

## 4. Requisitos Mínimos de Hardware e Software

### Servidor (máquina que roda a aplicação)

| Item | Mínimo recomendado |
|---|---|
| Sistema operacional | Windows 10 Pro / Windows 11 Pro (64 bits) |
| Processador | Intel Core i3 de 8ª geração ou equivalente |
| Memória RAM | 4 GB (8 GB recomendado para PostgreSQL) |
| Armazenamento | 20 GB livres para dados + backups locais |
| Rede | Placa de rede com IP fixo na rede interna |
| Python | 3.11 ou superior |
| PostgreSQL | 15 ou superior (Opção A) |

### Computadores dos usuários (clientes)

| Item | Mínimo |
|---|---|
| Navegador | Chrome 110+, Edge 110+ ou Firefox 115+ |
| Acesso | Rede interna cabeada ou Wi-Fi |
| Sem instalação adicional | A interface roda no navegador |

---

## 5. Riscos e Controles

| Risco | Probabilidade | Impacto | Controle proposto |
|---|---|---|---|
| Falha de disco no servidor | Média | Alto | Backup diário automatizado + cópia em HD externo rotativo |
| Acesso não autorizado à rede interna | Baixa | Alto | Autenticação obrigatória, senhas fortes, log de auditoria |
| Importação XLSX com dados incorretos | Alta | Médio | Validação atômica: rejeitar arquivo inteiro se houver erro |
| Atualização quebra funcionalidade existente | Média | Médio | Testes automatizados com dados fictícios antes de toda atualização |
| Perda de senha de administrador | Baixa | Alto | Procedimento documentado de recuperação; manter responsável de backup |
| Crescimento de dados além do SQLite | Média | Médio | Migração planejada para PostgreSQL (Opção B → A) |
| Conflito de escrita simultânea (SQLite) | Média | Médio | Limitar ações simultâneas na fase inicial; monitorar erros de bloqueio |
| Exposição de dados em repositório | Baixa | Crítico | `.gitignore` rigoroso; proibição de dados reais no GitHub (ver SECURITY.md) |

---

## 6. Decisões que Ainda Exigem Aprovação Humana

Nenhuma das decisões abaixo está aprovada. São **propostas** que precisam de validação do responsável técnico, farmacêutico responsável e, quando aplicável, do responsável pela segurança da informação:

1. **Escolha entre PostgreSQL e SQLite** — depende do perfil técnico disponível para manutenção.
2. **Política de backup** — frequência, destino (HD externo, NAS, outro) e responsável pelo teste mensal de restauração.
3. **Política de senhas e expiração** — critérios de complexidade e periodicidade de troca.
4. **Pseudonimização de pacientes** — estratégia (hash, ID interno, tabela separada) e quem detém a chave de reversão.
5. **Perfis de acesso** — quais funções têm permissão de importar, visualizar, aprovar compras, gerar relatórios.
6. **Computador designado como servidor** — especificações, localização física, controle de acesso físico.
7. **Plano de continuidade** — o que acontece se o servidor ficar indisponível (processo manual temporário).
8. **Escolha de framework de front-end** — HTML puro com Jinja2 (embutido no FastAPI) vs. React/Vue separado.
9. **Conformidade com LGPD e regulamentações de saúde** — validação jurídica e farmacêutica antes de qualquer dado real.

---

## 7. Proposta de ADR — Ainda Não Aprovada

### ADR-001: Banco de dados para o MVP local

**Status:** PROPOSTA — não aprovada

**Contexto:**
O MVP precisa de um banco de dados que funcione localmente no Windows, suporte múltiplos usuários na rede interna, ofereça backups confiáveis e seja mantível por uma equipe pequena sem infraestrutura de nuvem.

**Opções consideradas:**
- A: PostgreSQL 15+
- B: SQLite (embutido)
- C: MySQL/MariaDB (descartado por não oferecer vantagem relevante sobre PostgreSQL neste cenário)

**Decisão proposta:**
PostgreSQL 15+ como banco principal (Opção A), com SQLite como contingência na fase inicial se a equipe não tiver capacidade técnica imediata para manter PostgreSQL.

**Consequências esperadas:**
- Positivas: concorrência, controle de acesso, backup robusto, escalabilidade gradual.
- Negativas: instalação mais complexa; requer serviço em execução constante no Windows.

**Critérios de aceitação desta ADR:**
- [ ] Responsável técnico confirma capacidade de instalar e manter PostgreSQL no Windows.
- [ ] Política de backup definida e testada com dados fictícios.
- [ ] Aprovação do responsável pela segurança da informação.
- [ ] Registro em ata ou documento assinado pelo responsável do projeto.

**Revisor obrigatório:** Responsável técnico + Farmacêutico responsável + Responsável pela segurança da informação.

---

> **Aviso:** Este documento é uma recomendação técnica de planejamento. Não substitui avaliação médica, farmacêutica, jurídica ou regulatória. Nenhuma compra, implantação, acesso a dados reais ou decisão clínica deve ser baseada exclusivamente neste documento. Toda decisão listada na seção 6 exige aprovação humana documentada antes de qualquer implementação.
