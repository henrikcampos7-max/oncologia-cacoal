# ROADMAP.md

> Projeto: gestão de oncologia — Cacoal/RO (Unimed). Fases 0–12 concluídas no núcleo. A cada fase concluída, mova para "Concluído", crie a próxima Issue e arquive no GH.

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
10. Conferência automatizada de transferências (Ji-Paraná → Cacoal): máquina de estados, parser do relatório PDF (validado com PDF real), evidências com providers de visão, reconciliação, divergências auditadas, aprovação e integração ao estoque.
11. OCR real plugável: providers Azure Document Intelligence e Google Cloud Vision implementando `ProviderBase`, configuráveis por env, com parser conservador e testes determinísticos sem API paga.
12. Auditoria com integridade técnica: log append-only com cadeia de hashes SHA-256, verificação por comando e na tela, bloqueio de edição/exclusão (pendência A03 da revisão de qualidade fechada).

## Fases pendentes
- Nenhuma no núcleo. Evoluções futuras: alertas avançados e integrações opcionais (WhatsApp fora do MVP).

## Próxima
- Testar os providers externos (Azure/Google) com chave real em homologação e calibrar limiares de confiança por campo (`TRANSFER_VISION_PROVIDER`, `TRANSFER_AZURE_*`, `TRANSFER_GOOGLE_TOKEN`).
