# CONTINUAR ONCOLOGIA CACOAL NO GITHUB

## Destino autorizado

- Trabalhar somente no repositório local `C:\Users\henri\Documents\Codex\2026-07-29\concon\oncologia-cacoal`.
- Repositório remoto já existente: `henrikcampos7-max/oncologia-cacoal`.
- Continuar a partir da branch local `feature/modelo-oncomanager-unimed` ou de uma nova branch derivada dela após revisar o estado.
- Não enviar comandos ao Lovable, não alterar projetos de terceiros e não publicar automaticamente.
- Não fazer push, merge, implantação ou abrir o sistema para dados reais sem autorização expressa.

## Arquitetura e identidade

- Preservar Django 5.2 LTS com páginas renderizadas no servidor e PostgreSQL.
- Usar a identidade da Unimed Centro Rondônia já armazenada em `branding/`.
- Seguir `docs/ESPECIFICACAO_MODELO_ONCOMANAGER_UNIMED.md` para o leiaute e os fluxos inspirados nas imagens.
- Não copiar código, nome, marca ou ativos do OncoManager restrito.

## Estado implementado

- Modelos iniciais de clínica, perfis, medicamentos, apresentações, protocolos, pacientes e sessões.
- Tela de acesso própria, com login por usuário/e-mail e criação de conta controlada pelo administrador.
- Painel, navegação responsiva, agenda, exportação CSV, impressão/PDF, pacientes, medicamentos e quantitativo.
- Cálculos puros testados para superfície corporal, dose por tipo e arredondamento de frascos.
- Páginas de escopo para estoque, transferências, compras, importações, alertas, relatórios e auditoria.

## Próximas etapas

1. Configurar PostgreSQL local e aplicar as migrações.
2. Criar clínica, usuário e perfil administrativo apenas com dados fictícios.
3. Verificar visualmente as páginas em computador e celular.
4. Implementar cadastro de protocolos e itens repetíveis de medicamentos.
5. Implementar estoque, posições, movimentações, reservas, lotes e validades.
6. Implementar transferências, compras, pedidos e recebimentos.
7. Implementar importação Excel/CSV com prévia, mapeamento, duplicidades e conciliação.
8. Implementar alertas, relatórios, permissões completas e auditoria transacional.
9. Ampliar testes de isolamento por clínica, cálculos críticos e acesso indevido.

## Regras obrigatórias

- Usar somente dados fictícios em código, testes e demonstrações.
- Nunca armazenar no Git informações de pacientes, prescrições, planilhas operacionais, senhas ou segredos.
- Não alterar dose, protocolo, equivalência, estoque ou compra automaticamente.
- Manter validação humana, rastreabilidade e critérios de aceite em toda operação crítica.

