# DEVELOPMENT_STATUS.md

> Manter este arquivo curto. Ele é a memória operacional do projeto.

## Status geral
Projeto em desenvolvimento. Fases 0–10 concluídas no núcleo (incluindo o módulo de conferência automatizada de transferências).

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
- **Fase 9 — Operação**: relatórios com navegação por mês, exportação CSV do consumo mensal (`relatorios_consumo_csv`) e métricas administrativas (sobras, compras, transferências, taxa de presença).
- **Fase 10 — Conferência automatizada de transferências (Ji-Paraná → Cacoal)**:
  - Máquina de estados `Transferencia.status_conferencia` (`core/conferencia.py`) com transições validadas e sincronização do status legado.
  - Importação do relatório PDF (`core/relatorio_pdf.py` + `importar_transferencia_pdf`): extração por regex (descrição/lote/validade/quantidade), hash SHA-256 para deduplicação, referência externa e data de emissão; itens não reconhecidos viram pendências sem bloquear.
  - Resolução de nomes por cadastro local e aliases aprovados (`AliasMedicamento`).
  - Evidências fotográficas (`core/vision.py`): validação de tipo/tamanho, hash com suspeita de duplicidade, providers de extração plugáveis (Manual/Mock determinístico via `TRANSFER_VISION_PROVIDER`), versões de extração auditáveis (`ExtracaoEvidencia`).
  - Reconciliação (`core/reconciliacao.py`): comparativo esperado × observado, classificação de validade (ok/crítica/vencida/desconhecida), divergências tipadas com severidade e resolução auditada, derivação automática do estado (EM_CONFERENCIA/DIVERGENCIA/PRONTA_PARA_APROVACAO).
  - Aprovação e integração ao estoque: somente conferências aprovadas criam lotes e movimentações de entrada no destino.
  - Telas: importação do relatório, conferência (evidências → reconciliação → aprovação → estoque), links nas telas de transferências e admin para os novos registros.

## Parcial
- Nenhum item pendente nas fases concluídas.

## Em andamento
- Nenhum. Validação contínua da conferência automatizada em ambiente real (OCR externo via `TRANSFER_VISION_PROVIDER` quando disponível).

## Próxima Issue
- [ ] Validar o parser do relatório "rev. 77" com PDFs reais de Ji-Paraná e ajustar padrões de linha se necessário.
- [ ] Plugar provider de OCR real (ex.: Azure/Google) implementando `ProviderBase`.

## Backlog prioritário
- [ ] OCR real no pipeline de evidências (provider externo).
- [ ] Alertas avançados e integrações opcionais.

## Não priorizar agora
WhatsApp, dashboards sofisticados, notificações avançadas e integrações não essenciais.

## Decisões técnicas
- Cadastro central por clínica; multclínica via `PerfilUsuario`.
- `SobraReal` nunca altera estoque físico; entra no pool do motor apenas como sobra inicial.
- Importações são sempre em duas etapas (enviar → mapear/confirmar); a importação efetiva nunca roda direto do upload.
- Transferências importadas não baixam estoque automaticamente: exigem conferência (recebimento) com lote/validade.
- Conferência automatizada nunca inventa lote/validade: campos ausentes ficam vazios e exigem revisão humana antes da aprovação.
- Integração ao estoque só ocorre em transferências aprovadas; todo o histórico (evidências, extrações, divergências, resoluções) permanece auditável.

## Bloqueios
Nenhum registrado.