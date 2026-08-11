# DEVELOPMENT_STATUS.md

> Manter este arquivo curto. Ele é a memória operacional do projeto.

## Status geral
Projeto em desenvolvimento. Fases 0–8 concluídas; Fases 9–10 pendentes.

## Concluído
- **Fase 0 — Estabilização**: stack confirmada (Django + SQLite/Postgres), testes, README e docs.
- **Fase 1 — Fundação**: autenticação (login por usuário ou e-mail), perfis (Administrador, Farmacêutico, Auxiliar de farmácia, Enfermagem, Somente leitura), permissões por papel e auditoria mínima (`RegistroAuditoria`).
- **Fase 2 — Cadastros**: medicamentos, apresentações (com estabilidade após abertura), pacientes e protocolos.
- **Fase 3 — Tratamento e agenda**: sessões, ciclos, dias de ciclo, agenda e vínculo paciente → protocolo → medicamento → data; baixa de estoque FEFO com geração automática de sobra real.
- **Fase 4 — Estoque**: lotes, saldo, validade, movimentações, reservas (não alteram saldo físico), FEFO, transferências entre unidades, alertas de validade/estoque.
- **Fase 5 — Demanda**: motor de demanda individual e consolidada por apresentação com testes (`test_services`, `test_sobras_projetadas`).
- **Fase 6 — Sobras**: `SobraReal` (registro manual e automático na baixa de sessão), `SobraReal` no pool do motor, estabilidade, FEFO, reutilização/descarte com auditoria, integração com previsão e compras.
- **Fase 7 — Compra**: sugestão de compra = demanda líquida − estoque disponível + margem de segurança; pedidos de compra com itens, rascunho → enviado → recebido (cria/atualiza lotes no recebimento).
- **Fase 8 — Importações**:
  - Tipos de importação: Medicamentos, GMED (lista ANVISA) e Transferências (Ji-Paraná → Cacoal), registrados em `ImportacaoArquivo.tipo`.
  - Deduplicação por nome normalizado (acentos/caixa/espaços) em medicamentos e apresentações.
  - Transferências importadas criam `Transferencia.importada=True` (rascunho) sem baixa de estoque; dedup por documento na mesma origem.
  - Conciliação: página de importações lista transferências importadas pendentes com link para conferência/recebimento.
  - Fluxo: upload .xlsx → escolha da aba → mapeamento de colunas por tipo → prévia → confirmação com contadores (importadas/erros/duplicadas).

## Parcial
- Nenhum item pendente nas fases concluídas.

## Em andamento
- **Fase 9 — Operação** (parcial):
  - Relatórios com navegação por mês e exportação CSV do consumo mensal (relatorios_consumo_csv).
  - Novas métricas: sobras reutilizadas/descartadas (mg), pedidos de compra criados/recebidos, transferências recebidas e taxa de presença.
  - Conciliação de transferências importadas: recebimento direto de documentos importados em rascunho (sem baixa na origem), formando lotes no destino.
  - Pendente: lista de compras consolidada e integrações avançadas (Fase 10).

## Próxima Issue
- [ ] Fase 9: revisar lista consolidada de compras/projeções e examinar indicadores adicionais.

## Backlog prioritário
- [ ] Fase 9: relatórios e indicadores administrativos ampliados
- [ ] Fase 10: alertas avançados e integrações opcionais

## Não priorizar agora
WhatsApp, dashboards sofisticados, notificações avançadas e integrações não essenciais.

## Decisões técnicas
- Cadastro central por clínica; multclínica via `PerfilUsuario`.
- `SobraReal` nunca altera estoque físico; entra no pool do motor apenas como sobra inicial.
- Importações são sempre em duas etapas (enviar → mapear/confirmar); a importação efetiva nunca roda direto do upload.
- Transferências importadas não baixam estoque automaticamente: exigem conferência (recebimento) com lote/validade.

## Bloqueios
Nenhum registrado.