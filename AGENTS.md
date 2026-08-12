# Oncologia Cacoal — regras de trabalho neste computador

Este computador é o **POSTO FARMÁCIA**. O outro computador trabalha em paralelo no mesmo repositório.

## Regra obrigatória

- Trabalhar sempre na branch **`farmacia`** (nunca em `main`).
- A cada andamento concluído (tarefa, fix, etapa de implementação):
  1. `git add .`
  2. `git commit -m "mensagem descritiva"`
  3. `git push` para `origin/farmacia`
- Antes de começar uma sessão: `git pull --rebase origin farmacia` para sincronizar.
- Conferir com `git status` se a branch atual é `farmacia`.

## Conflitos com o outro computador

- O outro computador não deve editar esta mesma branch simultaneamente sem avisar.
- Se houver conflito ao puxar, resolvê-lo manualmente antes de continuar.
- Não mesclar `farmacia` em `main` sem autorização expressa.

## Estado do projeto

- Django 5.2 LTS, app Django em `oncologia_cacoal/`, regras de negócio em `core/services.py`.
- Docs de estado: `docs/DEVELOPMENT_STATUS.md` e `docs/ROADMAP.md`.
- Próximas etapas documentadas no `DEVELOPMENT_STATUS.md` (seguir o backlog).