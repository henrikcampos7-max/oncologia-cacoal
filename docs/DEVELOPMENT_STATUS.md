# DEVELOPMENT_STATUS.md

> Manter este arquivo curto. Ele é a memória operacional do projeto.
> Estado confirmado contra o repositório real em 2026-08-12 (198 testes automatizados passando).

## Status geral
Projeto em desenvolvimento. Base administrativa operacional completa e testada; motor de sobras projetadas integrado à previsão de compra; faltam sobras reais e a timeline de reaproveitamento.

## Concluído
- [x] Autenticação por email (login/logout) e recuperação de acesso via aprovação administrativa
- [x] Perfis e permissões por papel (Administrador, Farmacêutico, Auxiliar, Enfermagem, Gestor, Leitura)
- [x] Pacientes (cadastro, edição, superfície corporal Mosteller)
- [x] Medicamentos e apresentações (cadastro e edição, doses por peso/SC, estabilidade após abertura com unidade, armazenamento, observações e fonte/referência)
- [x] Protocolos e itens (dose fixa, mg/kg, mg/m²; ciclos; dias do ciclo)
- [x] Agenda de sessões (registro, filtros, CSV, impressão, confirmar/realizar/cancelar/faltou com motivo e baixa FEFO de estoque na realização)
- [x] Estoque: lotes com validade e mínimo, movimentações (entrada, saída, perda, ajuste, reserva), reserva sem alterar saldo físico, disponível/reservado
- [x] Compras: sugestão automática com reaproveitamento de sobras projetadas, pedido com itens e número, rascunho → pendente → aprovado, aprovação por Admin/Gestor, auditoria
- [x] Motor de sobras projetadas: agenda → doses → abertura virtual de frascos → sobra com limite de estabilidade → reaproveitamento FEFO automático → perda projetada → necessidade final de frascos (sem alterar estoque físico e sem conciliação manual)
- [x] Transferências entre unidades (rascunho → em trânsito → recebida; cancelamento; baixa FEFO na origem; entrada com lote na destino)
- [x] Importação de planilhas XLSX (upload, inspeção de abas, mapeamento de colunas, importação com erros linha a linha, histórico)
- [x] Auditoria transacional (cadastros, movimentações, status, fluxos) com tela de consulta
- [x] Alertas (página com vencidos/críticos/baixos + envio por email manual e comando agendável `enviar_alertas_email`)
- [x] Relatórios gerenciais (indicadores, taxas de faltas/cancelamento, consumo mensal, estoque por validade/quantidade, lotes urgentes)
- [x] Painel inicial (dashboard)
- [x] Kit de agentes de desenvolvimento em `.github/agents/` (27) + instruções Copilot em `.github/copilot-instructions.md`
- [x] 13 referências visuais fictícias mapeadas para 15 agentes orquestradores/QA e 18 skills modulares/transversais, com Modo de Economia de Tokens, acessibilidade e barreiras de segurança/LGPD
- [x] Medicações orais: agenda, filtros, classes, ciclos e prazos previstos, estratégia de aquisição, prioridade humana, revisão/status manual e auditoria
- [x] Configurações por clínica: painel, densidade, alertas, preferências, acesso administrativo e auditoria; sem exibir credenciais
- [x] Filtros funcionais nas telas de pacientes, medicamentos, estoque e auditoria
- [x] Exportações reais: agenda/quantitativo/auditoria/consumo CSV, resumo Excel, impressão/PDF e cópia administrativa JSON sem credenciais
- [x] Segurança de produção: HTTPS, cookies seguros e HSTS configuráveis por ambiente

## Parcial
- [ ] Quantitativo/previsão: resumo por período e exportação disponíveis, sem motor de demanda consolidada formal
- [ ] Sem estabilidade cadastrada, o motor marca `ESTABILIDADE_NAO_CADASTRADA` e não reaproveita (cadastro clínico fica a cargo do farmacêutico)

## Não implementado
- [ ] Sobras reais (cadastro, origem, abertura, estabilidade, armazenamento, status, rastreabilidade origem → destino)
- [ ] Timeline gráfica do reaproveitamento (eventos já estruturados no resultado do motor)
- [ ] Combinação/otimização entre múltiplas apresentações do mesmo medicamento na simulação
- [ ] Demanda individual formal por paciente e consolidação por medicamento
- [ ] Modelos DemandForecast / Leftover / LeftoverAllocation (previstos na arquitetura)

## Bugs / Bloqueios
- Nenhum bloqueio de código conhecido nesta entrega. Produção ainda exige infraestrutura protegida e revisão humana antes de publicar.

## Próxima Issue
- [ ] Cadastro de sobras reais (modelo Leftover) integrado ao pool do motor via `sobras_iniciais`

## Backlog prioritário
- [ ] Sobras reais (próxima Issue)
- [ ] Estabilidade e status de sobras reais
- [ ] Timeline de reaproveitamento (usar `eventos` do motor)
- [ ] Combinação de múltiplas apresentações no motor
- [ ] Demanda individual e consolidada por medicamento
- [ ] Demanda líquida e previsão de compra com margem configurável
- [ ] Recebimento de pedidos gerando lotes
- [x] Impressão e exportação dos relatórios

## Não priorizar agora
WhatsApp, dashboards sofisticados, notificações avançadas e integrações não essenciais.

## Decisões técnicas
- Django 5.2 LTS + PostgreSQL em produção; SQLite apenas em desenvolvimento/testes
- Regras de negócio centralizadas em `core/services.py` (motores de dose, estoque, sobras projetadas, importação, alertas, compras)
- Motor de sobras: `calcular_previsao_sobras(clinica, dias)` → resultado por apresentação com eventos (abertura, reuso, perda), FEFO por limite de estabilidade, reuso inclusivo no limite
- Estabilidade cadastrada em `Apresentacao` (mg, unidade horas/dias, armazenamento, observações, fonte); ausência = sem reaproveitamento (flag `ESTABILIDADE_NAO_CADASTRADA`)
- Auditoria via `registrar_auditoria`; transações para movimentações críticas
- Baixa de estoque FEFO por data de validade; reserva não altera saldo físico
- Simulação nunca altera estoque físico nem exige conciliação manual
- CI via GitHub Actions roda `manage.py check` e suíte de testes a cada push

## Bloqueios
- Publicação do Django depende da escolha/configuração do ambiente de hospedagem e de segredos externos; isso não foi automatizado nem versionado.
