# Recomendação Técnica Comparativa — MVP Oncologia Cacoal

> **Status:** Aprovada em 2026-08-09 para iniciar o desenvolvimento com Django + PostgreSQL. Implantação e uso de dados reais continuam condicionados às revisões descritas neste documento.
> **Data:** 2026-08-09
> **Autor:** Agente planejador-arquitetura (revisão humana obrigatória antes de qualquer implementação)

---

## 1. Estrutura da Análise

A análise é organizada em dois eixos independentes:

- **Eixo A — Framework de aplicação/interface:** como a equipe construirá a lógica de negócio, telas, formulários, autenticação e administração.
- **Eixo B — Banco de dados:** onde os dados serão armazenados, com qual nível de concorrência e robustez de backup.

As opções de cada eixo podem ser combinadas. A tabela comparativa abaixo apresenta as combinações mais relevantes para o cenário (intranet local, equipe pequena, Windows).

---

## 2. Tabela Comparativa

### Eixo A — Framework de aplicação

| Critério | Opção A1 — Django (páginas renderizadas no servidor) | Opção A2 — FastAPI + Jinja2 (páginas renderizadas) | Opção A3 — FastAPI (API) + SPA separada |
|---|---|---|---|
| **Autenticação e sessões** | Embutidas: sistema de usuários, grupos, permissões e CSRF prontos | Requer implementação manual ou biblioteca adicional (ex.: `fastapi-users`) | Requer implementação em dois projetos (API + front-end) |
| **Administração** | Painel `/admin` gerado automaticamente para CRUD de dados | Sem painel automático; requer templates manuais | Sem painel automático; requer front-end dedicado |
| **Formulários e validação** | `django.forms` com CSRF, validação server-side e feedback de erro prontos | Pydantic para validação de dados; templates Jinja2 manuais | Pydantic + lógica de formulário no front-end (JavaScript) |
| **Migrações de banco** | `manage.py makemigrations` / `migrate` integrado e auditável | Alembic separado, maduro, porém exige configuração adicional | Alembic separado (igual ao A2) |
| **Trabalho personalizado** | **Mínimo:** autenticação, admin e CSRF já resolvidos pelo framework | **Médio:** mais código de "cola" para auth, admin e proteção CSRF | **Alto:** duas bases de código, CORS, autenticação por token |
| **Curva de aprendizado** | Moderada: convenções Django; documentação extensa em português | Baixa para API; moderada para templates | Alta: domínio de FastAPI + React/Vue + CORS + JWT |
| **Adequação a intranet local** | Alta: renderização server-side sem dependência de CDNs ou build JS | Alta: mesma vantagem de renderização server-side | Média: SPA exige build JS e pode depender de CDN para desenvolvimento |
| **Licença** | BSD 3-Clause | MIT | MIT + licença do SPA escolhido |
| **Evolução sem reescrita** | Alta: REST API e GraphQL possíveis no mesmo projeto | Alta: migração para SPA possível mantendo a API | Alta: front-end e back-end evoluem independentemente |

### Eixo B — Banco de dados

| Critério | Opção B1 — PostgreSQL (versão principal com suporte ativo) | Opção B2 — SQLite (embutido) |
|---|---|---|
| **Concorrência na rede interna** | Alta: múltiplos usuários simultâneos sem degradação de escrita | Limitada: bloqueios em escritas simultâneas; adequado para poucos usuários |
| **Instalação no Windows** | Moderada: instalador oficial disponível; exige serviço em execução contínua | Nenhuma: arquivo embutido na aplicação |
| **Controle de acesso** | Granular: usuários, roles e permissões no nível do banco | Na camada de aplicação; arquivo `.db` protegido por permissões de SO |
| **Backup e recuperação** | Robusto: `pg_dump`, WAL archiving, recuperação point-in-time | Simples: copiar o arquivo `.db`; sem recuperação point-in-time |
| **Versão recomendada** | Versão principal atualmente suportada, sempre no minor release atual (ver [política oficial](https://www.postgresql.org/support/versioning/)) | N/A (sem versionamento separado) |
| **Política de atualização** | Acompanhar o calendário de fim de suporte de cada versão principal; planejar migração antes do EOL | Atualiza com a biblioteca Python embutida |
| **Migração SQLite → PostgreSQL** | N/A | Possível sem reescrever a API, desde que o ORM seja configurado de forma portável |
| **Licença** | PostgreSQL License (similar a BSD/MIT) | Domínio público |

---

## 3. Recomendação Principal e Alternativa de Contingência

> **Decisão registrada:** Django + PostgreSQL foi aprovado pelo responsável do projeto em 2026-08-09. A contingência não foi adotada.

### Recomendação principal — A1 + B1: Django + PostgreSQL

**Justificativa:**
- Django reduz ao mínimo o trabalho personalizado de autenticação, administração, formulários, proteção CSRF e migrações — vantagem crítica para equipe pequena sem back-end dedicado.
- O painel `/admin` gerado automaticamente permite validar fluxos de dados antes de qualquer tela customizada.
- PostgreSQL suporta múltiplos usuários simultâneos na rede interna sem degradação de escrita.
- Controle de acesso em duas camadas: permissões do Django e roles do PostgreSQL.
- `pg_dump` automatizado via Agendador de Tarefas do Windows garante backups confiáveis.
- Migrações auditáveis com histórico (`manage.py makemigrations`).
- Ecossistema Python amplamente documentado para equipes de saúde e dados.

**Pré-condições para adoção:**
- Responsável técnico capaz de instalar e manter PostgreSQL no Windows.
- Política de backup definida, criptografada e testada antes de qualquer dado real.
- Aprovação documentada do responsável pela segurança da informação.

### Alternativa de contingência — A2 + B2: FastAPI + Jinja2 + SQLite

**Justificativa:**
- Menor exigência técnica inicial: sem serviço de banco externo para gerenciar.
- FastAPI + Jinja2 mantém renderização server-side, evitando complexidade de SPA.
- Migração para PostgreSQL possível sem reescrever a API, desde que o ORM seja portável desde o início.
- Adequada enquanto o número de usuários simultâneos for baixo (≤ 3 escritas concorrentes).

**Limitações a monitorar:**
- Autenticação e CSRF exigem implementação manual, aumentando superfície de vulnerabilidade se feitos sem cuidado.
- Bloqueios de escrita em importações XLSX simultâneas.
- Arquivo `.db` precisa de permissões de SO restritas.
- Sem recuperação point-in-time nativa.

---

## 4. Arquitetura de Implantação Local e Rede Interna

```
Computadores da equipe (navegadores)
        │  HTTPS na rede interna (porta 443 ou 8443)
        │  [HTTP permitido somente em localhost/dev com dados fictícios]
        ▼
  Firewall do servidor
  - Aceita conexões somente de IPs autorizados na rede interna
  - Bloqueia qualquer acesso direto à internet de entrada
        │
        ▼
  Servidor local (computador dedicado ou estação designada — IP fixo)
  ┌──────────────────────────────────────────────────┐
  │  Aplicação Web (Django ou FastAPI / Python)      │
  │  - Interface HTML renderizada no servidor        │
  │  - Autenticação, sessões e controle de acesso    │
  │  - Processamento atômico de importações XLSX     │
  │  - Log de auditoria de todas as ações            │
  ├──────────────────────────────────────────────────┤
  │  Banco de dados (PostgreSQL ou SQLite)           │
  │  - Medicamentos, lotes, movimentações, auditoria │
  │  - Backup diário automatizado e criptografado    │
  └──────────────────────────────────────────────────┘
        │
        ▼
  Mídia de backup fora do servidor principal
  (HD externo ou NAS com guarda física controlada —
   não pode ser a única cópia; rotação e teste mensal obrigatórios)
```

**Fluxo de acesso:**
1. Usuário abre o navegador em seu computador e acessa o endereço HTTPS do servidor na rede interna.
2. A aplicação exige login com credenciais individuais (senha longa ou frase; MFA quando viável).
3. O firewall do servidor verifica se o IP de origem está na lista de origens permitidas.
4. Cada ação fica registrada no log de auditoria com usuário, data/hora e operação.
5. Dados nunca saem da rede interna; sem dependência de internet para operação.
6. O servidor não deve ter nenhuma porta exposta diretamente à internet.

---

## 5. Requisitos Mínimos de Hardware e Software

### Servidor (máquina que roda a aplicação)

| Item | Mínimo | Preferível |
|---|---|---|
| **Sistema operacional** | Windows 11 Pro/Enterprise (64 bits) com suporte ativo | Windows Server ainda suportado pela Microsoft |
| **Nota sobre Windows 10** | Somente como exceção formal coberta por ESU (Extended Security Updates); nunca como baseline de implantação normal. Referência: [Microsoft — fim do suporte Windows 10](https://learn.microsoft.com/en-us/lifecycle/announcements/windows-10-end-of-support) | — |
| **Processador** | Intel Core i5 de 10ª geração ou equivalente AMD | Core i7 ou servidor dedicado |
| **Memória RAM** | 8 GB | 16 GB |
| **Armazenamento** | 50 GB livres (aplicação + banco + logs) | SSD com monitoramento de saúde do disco ativado |
| **Rede** | Placa de rede com IP fixo na rede interna | Redundância de rede ou UPS |
| **Python** | 3.12 ou superior (versão com suporte ativo) | — |
| **PostgreSQL** | Versão principal com suporte ativo no minor release atual (ver [política oficial](https://www.postgresql.org/support/versioning/)) | — |
| **TLS/HTTPS** | Certificado confiável em todos os dispositivos clientes, emitido por CA interna gerenciada; certificado próprio somente com distribuição segura da raiz de confiança nos clientes — nunca orientar usuários a ignorar avisos de certificado | CA interna com renovação automatizada |

### Computadores dos usuários (clientes)

| Item | Requisito |
|---|---|
| **Navegador** | Versão atualmente suportada e atualizada do Chrome, Edge ou Firefox |
| **Acesso** | Rede interna cabeada ou Wi-Fi |
| **Sem instalação adicional** | A interface roda no navegador |

---

## 6. Segurança, TLS e Política de Senhas

### Canal de comunicação

- **HTTPS/TLS obrigatório** para qualquer acesso à aplicação na rede interna com dados reais.
- HTTP permitido **somente** em ambiente de localhost/desenvolvimento com dados exclusivamente fictícios.
- O servidor não deve expor portas diretamente à internet; acesso externo, se necessário, somente por VPN com aprovação documentada.
- Firewall configurado com lista de origens (IPs) permitidos na rede interna; demais origens bloqueadas por padrão.
- Controle de acesso físico ao servidor: sala ou armário com acesso restrito.

### Política de senhas (alinhada ao NIST SP 800-63B)

Referência: [NIST SP 800-63B — Authenticators](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/)

- **Comprimento mínimo:** 15 caracteres quando a senha for o único fator de autenticação; 8 caracteres quando fizer parte de MFA. Permitir pelo menos 64 caracteres; incentivar frases longas.
- **Verificação contra listas de senhas comprometidas** no cadastro e na troca, usando lista local/offline ou mecanismo que preserve privacidade (ex.: k-anonymity via API de hash parcial). A senha completa nunca deve ser enviada a serviço externo.
- **Sem exigência de troca periódica arbitrária;** exigir troca somente quando houver evidência de comprometimento.
- **Bloqueio temporário** após número configurável de tentativas falhas (ex.: 5 tentativas → bloqueio progressivo).
- **Hash forte com salt** no armazenamento (ex.: bcrypt, Argon2 ou PBKDF2 com parâmetros atualizados).
- **MFA (autenticação multifator):** implementar quando viável; obrigatório para contas de administrador.
- **Sem dicas de senha** armazenadas; sem perguntas de segurança como único fator de recuperação.

---

## 7. Riscos e Controles

| Risco | Probabilidade | Impacto | Controle proposto |
|---|---|---|---|
| Falha de disco no servidor | Média | Alto | Backup diário, criptografado, fora do disco principal; HD externo com guarda física controlada; não pode ser a única cópia; teste mensal de restauração obrigatório |
| Acesso não autorizado à rede interna | Baixa | Alto | HTTPS/TLS obrigatório; autenticação individual; firewall com lista de IPs permitidos; log de auditoria; MFA para administradores |
| Importação XLSX com dados incorretos | Alta | Médio | Validação atômica: rejeitar arquivo inteiro se houver qualquer erro |
| Atualização quebra funcionalidade existente | Média | Médio | Testes automatizados com dados fictícios antes de toda atualização; ambiente de homologação separado |
| Perda de credencial de administrador | Baixa | Alto | Procedimento documentado de recuperação; MFA; segunda conta de administrador de emergência controlada |
| Crescimento de dados além do SQLite (Opção B2) | Média | Médio | Migração planejada para PostgreSQL sem reescrita da API |
| Conflito de escrita simultânea (SQLite) | Média | Médio | Limitar ações simultâneas na fase inicial; monitorar e registrar erros de bloqueio |
| Exposição de dados reais no repositório | Baixa | Crítico | `.gitignore` rigoroso; proibição absoluta de dados reais no GitHub (ver SECURITY.md); dados reais somente em banco de produção protegido, após aprovação formal |
| Sistema operacional sem suporte ativo | Média | Alto | Usar Windows 11 Pro/Enterprise ou Windows Server suportado; Windows 10 somente com ESU formal |
| Versão PostgreSQL próxima do fim de suporte | Média | Médio | Monitorar calendário de EOL; planejar migração antes do término do suporte |
| Ausência de modelagem de ameaças antes da produção | Alta | Alto | Realizar modelagem de ameaças e revisão de segurança/LGPD como pré-requisito para entrada de dados reais |

---

## 8. Decisões que Ainda Exigem Aprovação Humana

A escolha de **Django + PostgreSQL** está aprovada. Permanecem pendentes as decisões operacionais abaixo, que precisam de validação do responsável técnico, farmacêutico responsável e, quando aplicável, do responsável pela segurança da informação:

1. **Versão específica do PostgreSQL a adotar** — seguir versão principal com suporte ativo no momento da instalação.
2. **Política de backup** — frequência, criptografia, destino (HD externo, NAS ou outro), rotação, responsável e teste mensal de restauração.
3. **Política de senhas e MFA** — critérios operacionais, recuperação de conta e fator adicional.
4. **Mecanismo técnico de pseudonimização** — o farmacêutico responsável controlará o de-para em ambiente separado, mas o mecanismo ainda exige revisão de segurança.
5. **Computador designado como servidor** — especificações, localização física e controle de acesso físico.
6. **Plano de continuidade** — o que acontece se o servidor ficar indisponível (processo manual temporário documentado).
7. **Modelagem de ameaças e revisão de segurança/LGPD** — obrigatória antes de qualquer dado real entrar no sistema.
8. **Conformidade com LGPD e regulamentações de saúde** — validação jurídica e farmacêutica antes de qualquer dado real.

---

## 9. ADR-001 — Arquitetura Aprovada

### ADR-001: Framework de aplicação e banco de dados para o MVP local

**Status:** ACEITA em 2026-08-09 pelo responsável do projeto.

**Contexto:**
O MVP precisa de uma arquitetura que funcione localmente no Windows, suporte múltiplos usuários na rede interna, minimize trabalho personalizado de autenticação/admin/formulários para uma equipe pequena, ofereça backups confiáveis e não exija infraestrutura de nuvem.

**Opções consideradas:**

| Combinação | Framework | Banco |
|---|---|---|
| A1 + B1 (recomendada) | Django (renderização server-side) | PostgreSQL (versão com suporte ativo) |
| A2 + B2 (contingência) | FastAPI + Jinja2 (renderização server-side) | SQLite |
| A3 + B1 (descartada neste MVP) | FastAPI (API) + SPA separada | PostgreSQL |
| MySQL/MariaDB | — | Descartado: sem vantagem relevante sobre PostgreSQL neste cenário |

**Decisão:**
Django 5.2 LTS com páginas renderizadas no servidor e PostgreSQL como stack do MVP. FastAPI + SQLite permanece apenas como alternativa histórica analisada e não adotada.

**Consequências esperadas:**

- *Django + PostgreSQL:* autenticação, admin e CSRF prontos; concorrência adequada; backup robusto; maior esforço de instalação do PostgreSQL no Windows.
- *FastAPI + SQLite:* instalação mais simples; maior trabalho manual de autenticação e formulários; limitações de concorrência.

**Critérios de aceitação desta ADR:**
- [x] Responsável do projeto aprova Django + PostgreSQL.
- [ ] Responsável técnico confirma capacidade de instalação e manutenção do PostgreSQL.
- [ ] Versão do PostgreSQL definida como versão principal com suporte ativo no momento da implementação.
- [ ] Política de backup criptografado definida e testada com dados fictícios.
- [ ] Política de senhas documentada (alinhada ao NIST SP 800-63B).
- [ ] Modelagem de ameaças e revisão de segurança/LGPD concluídas antes de qualquer dado real.
- [ ] Aprovação do responsável pela segurança da informação.
- [ ] Registro em ata ou documento assinado pelo responsável do projeto.

**Revisores obrigatórios:** Responsável técnico + Farmacêutico responsável + Responsável pela segurança da informação.

**Referências:**
- [Microsoft — fim do suporte Windows 10](https://learn.microsoft.com/en-us/lifecycle/announcements/windows-10-end-of-support)
- [PostgreSQL — política de versões](https://www.postgresql.org/support/versioning/)
- [NIST SP 800-63B — Authenticators](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/)

---

> **Aviso:** Este documento registra a arquitetura aprovada para desenvolvimento, mas não substitui avaliação médica, farmacêutica, jurídica ou regulatória. Nenhuma compra, implantação, acesso a dados reais ou decisão clínica deve ser baseada exclusivamente neste documento. Dados reais somente podem entrar no banco de produção protegido após conclusão da modelagem de ameaças, revisão de segurança, validação LGPD e aprovação humana documentada. Toda decisão pendente da seção 8 exige aprovação antes da implantação correspondente.
