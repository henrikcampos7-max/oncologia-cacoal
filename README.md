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

A arquitetura **Django 5.2 LTS + PostgreSQL** foi aprovada em 2026-08-09. O repositório contém a base da aplicação, documentação funcional, identidade visual, modelos iniciais e uma primeira interface server-rendered para acesso, painel, agenda, pacientes, medicamentos e quantitativo. A aplicação ainda não foi implantada nem autorizada para dados reais.

Consulte [docs/DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md) para preparar o ambiente local com dados fictícios.

## Segurança

- Não incluir dados reais de pacientes, prescrições, credenciais ou planilhas operacionais.
- Usar somente dados fictícios em desenvolvimento e testes.
- O sistema deve apoiar rotinas administrativas e não tomar decisões clínicas.
- Alterações de dose, estoque, compra ou cadastro exigem validação humana.

Consulte [SECURITY.md](SECURITY.md) antes de adicionar dados ou integrações.

## Próximos passos

1. Instalar e configurar PostgreSQL para desenvolvimento local e aplicar as migrações.
2. Completar recuperação de acesso, protocolos e itens repetíveis por tratamento.
3. Implementar estoque, lotes, validades, compras, importações e auditoria transacional.
4. Adicionar somente dados fictícios e ampliar testes das regras críticas.
5. Validar segurança, LGPD e fluxos com responsáveis humanos antes de qualquer uso operacional.
