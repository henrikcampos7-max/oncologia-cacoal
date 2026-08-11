# ROADMAP.md

> Projeto: gestão de oncologia — Cacoal/RO (Unimed). Fases 0–10 concluídas no núcleo. A cada fase concluída, mova para "Concluído", crie a próxima Issue e arquive no GH.

## Fases concluídas
0. Estabilização e base esquemática do projeto.
1. Fundação: autenticação, perfis, permissões e auditoria.
2. Cadastros: medicamentos, apresentações, pacientes e protocolos.
3. Tratamento e agenda: sessões, ciclos, agenda e baixa FEFO.
4. Estoque: lotes, saldo, validade, reservas, transferências e alertas.
5. Demanda: motor de demanda individual/consolidada.
6. Sobras: pool de sobras reais integrado ao motor de previsão e à baixa de sessão.
7. Compra: sugestão {demanda − estoque + margem}, pedidos e recebimentos.
8. Importações: GMED (ANVISA), transferências Ji-Paraná → Cacoal, deduplicação e conciliação.
9. Operação: relatórios mensais, exportação CSV de consumo e indicadores administrativos.
10. Conferência automatizada de transferências (Ji-Paraná → Cacoal): máquina de estados, parser do relatório PDF, evidências com providers de visão, reconciliação, divergências auditadas, aprovação e integração ao estoque.

## Fases pendentes
- Nenhuma no núcleo. Evoluções futuras: OCR real (provider externo), lista consolidada de compras, alertas avançados e integrações opcionais (WhatsApp fora do MVP).

## Próxima
- Validar o parser do relatório "rev. 77" com PDFs reais de Ji-Paraná; ajustar padrões de linha se necessário.
- Plugar OCR real implementando `ProviderBase` (`core/vision.py`) e configurar `TRANSFER_VISION_PROVIDER`.
