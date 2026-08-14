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
  - Evidências fotográficas (`core/vision.py`): validação de tipo/tamanho, hash com suspeita de duplicidade, providers de extração plugáveis, versões de extração auditáveis (`ExtracaoEvidencia`).
  - Reconciliação (`core/reconciliacao.py`): comparativo esperado × observado, classificação de validade (ok/crítica/vencida/desconhecida), divergências tipadas com severidade e resolução auditada, derivação automática do estado (EM_CONFERENCIA/DIVERGENCIA/PRONTA_PARA_APROVACAO).
  - Aprovação e integração ao estoque: somente conferências aprovadas criam lotes e movimentações de entrada no destino.
  - Telas: importação do relatório, conferência (evidências → reconciliação → aprovação → estoque), links nas telas de transferências e admin para os novos registros.
- **Fase 11 — OCR real plugável**:
  - Providers externos implementando `ProviderBase` em `core/vision.py`: **Azure AI Document Intelligence** (prebuilt-layout) e **Google Cloud Vision** (TEXT_DETECTION), selecionados por `TRANSFER_VISION_PROVIDER=azure|google`.
  - Configuração exclusivamente por variável de ambiente (nenhuma chave versionada); falhas de configuração/rede geram `RuntimeError` com orientação e marcam a evidência como FALHOU (nenhum campo é inventado).
  - Parser conservador do texto OCR: lote validado (3–12 alfanuméricos), validade em formatos brasileiros (dd/mm/aaaa, mm/aaaa), quantidade somente quando rotulada; ausências exigem revisão humana.
  - Proxy HTTP injetável para testes determinísticos (sem chamadas pagas em CI).
- **Fase 12 — Auditoria com integridade técnica (A03)**:
  - `RegistroAuditoria` agora é **append-only**: edição e exclusão bloqueadas no modelo (`PermissionDenied`) e no admin (somente leitura).
  - Cadeia de hashes SHA-256: cada registro guarda `hash_anterior` (hash do registro anterior da clínica) e `hash_registro`; alteração manual em qualquer campo quebra a cadeia e é detectável.
  - `RegistroAuditoria.verificar_integridade(clinica)` + comando `manage.py verificar_integridade_auditoria` + indicador na tela de auditoria.
- **Fase 13 — Edições e relações operacionais**:
  - Agenda com cadastro destacado, edição bloqueada após encerramento, transições concorrentes protegidas e reconfirmação obrigatória quando uma sessão confirmada é alterada.
  - Medicamentos/apresentações com estabilidade após abertura e observações; lotes editáveis sem sobrescrever saldo ou histórico de movimentações.
  - Medicações orais com dose/posologia transcritas, unidades de estoque por ciclo, troca versionada de medicamento e preservação da versão anterior.
  - Previsão quantitativa inclui ciclos orais vigentes; ciclos passados e versões substituídas não entram novamente na compra.
  - Relações CSV por período para pacientes, agenda, catálogo de medicamentos, medicações orais, medicamento específico e estoque, com isolamento por clínica, permissões e neutralização de fórmulas.
  - Auditoria registra antes/depois das edições, filtros de exportação e ações identificadas; tela e exportação restritas a perfis autorizados.

## Parcial
- Publicação operacional depende de revisão humana, aplicação das migrações e configuração de hospedagem/segredos.

## Em andamento
- Revisão e homologação da Fase 13. OCR real disponível via providers Azure/Google; ativar com `TRANSFER_VISION_PROVIDER` e as variáveis de credencial do provider escolhido.

## Próxima Issue
- [x] Validar o parser do relatório com PDFs reais de Ji-Paraná e ajustar padrões de linha (fixture real `transferencia_jiparana_02-07.pdf` validada: 16 itens, 11 medicamentos, todos com lote).
- [x] Plugar provider de OCR real (Azure/Google) implementando `ProviderBase`.
- [ ] Testar os providers externos com uma chave real em homologação (Azure e/ou Google) e calibrar os limiares de confiança por campo.

## Backlog prioritário
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
- OCR externo nunca libera entrada no estoque sozinho: `IA extrai → sistema compara → farmacêutico valida → somente então estoque é atualizado`.
- Log de auditoria é append-only com hash encadeado; qualquer alteração manual é detectável via `verificar_integridade`.
