# Oncologia Cacoal

Projeto em fase de planejamento de um MVP administrativo para previsão de demanda, controle de estoque e apoio às compras de medicamentos oncológicos.

## Escopo previsto

- importação e validação de dados;
- agenda e tratamentos;
- medicamentos e apresentações;
- estoque, movimentações, lotes e validade;
- reservas, compras e alertas;
- auditoria e relatórios.

## Estado atual

A arquitetura **Django 5.2 LTS + PostgreSQL** foi aprovada em 2026-08-09. O repositório contém a base da aplicação, documentação funcional, identidade visual e uma interface server-rendered com:

- autenticação por email + administração de perfis/clínicas;
- painel e agenda de sessões de tratamento;
- pacientes, medicamentos, apresentações, protocolos e itens;
- estoque com movimentações, lotes, validades, reservas e alertas;
- compras com pedido e aprovação; sugestão automática de compras;
- transferências entre unidades (rascunho, em trânsito, recebida);
- solicitação/recuperação de acesso com aprovação administrativa;
- importação de planilhas XLSX com mapeamento de colunas e histórico;
- auditoria transacional e testes automatizados (48 testes).

A aplicação ainda não foi implantada nem autorizada para dados reais.

## Desenvolvimento

Consulte [docs/DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md) para preparar o ambiente local com dados fictícios.

### Rodar os testes

```powershell
$env:DJANGO_DEBUG = "true"
& ".venv\Scripts\python.exe" manage.py test core
```

A cada push para `main`, o [GitHub Actions](.github/workflows/ci.yml) roda `manage.py check` e a suíte de testes (Python 3.13, SQLite).

## Segurança

- Não incluir dados reais de pacientes, prescrições, credenciais ou planilhas operacionais.
- Usar somente dados fictícios em desenvolvimento e testes.
- O sistema deve apoiar rotinas administrativas e não tomar decisões clínicas.
- Alterações de dose, estoque, compra ou cadastro exigem validação humana.

Consulte [SECURITY.md](SECURITY.md) antes de adicionar dados ou integrações.

## Próximos passos

1. Instalar e configurar PostgreSQL para desenvolvimento local e aplicar as migrações.
2. Incrementar agenda com marcação de faltas e cancelamentos de sessões.
3. Relatórios gerenciais e notificações/alertas por email.
4. Adicionar somente dados fictícios e ampliar testes das regras críticas.
5. Validar segurança, LGPD e fluxos com responsáveis humanos antes de qualquer uso operacional.