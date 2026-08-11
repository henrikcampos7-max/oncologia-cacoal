# SKILLS — Biblioteca de habilidades reutilizáveis

Cada skill deve ser implementada como função/serviço pequeno, testável e desacoplado, respeitando a stack existente.

## SKILL 01 — parse_transfer_report
Entrada: arquivo de relatório.
Saída: metadados + linhas estruturadas + raw text.
Garantias: idempotência e rastreabilidade de linha.

## SKILL 02 — hash_source_file
Calcula SHA-256 e detecta arquivo idêntico já importado.

## SKILL 03 — normalize_transfer_description
Preserva descrição original e produz nome/apresentação normalizados.

## SKILL 04 — resolve_product_alias
Mapeia descrição para cadastro mestre usando aliases e confidence.

## SKILL 05 — split_presentation
Extrai concentração, volume, forma e embalagem quando possível.

## SKILL 06 — validate_image_upload
Valida tamanho, MIME, formato e integridade.

## SKILL 07 — assess_image_quality
Avalia foco, resolução, exposição, oclusão e legibilidade.

## SKILL 08 — decode_gs1
Decodifica GTIN/lote/validade quando presentes.

## SKILL 09 — decode_barcode_or_qr
Extrai conteúdo estruturado sem depender de OCR.

## SKILL 10 — extract_visible_medication
Extrai produto/princípio ativo/apresentação.

## SKILL 11 — extract_lot
Extrai lote sem preencher caracteres incertos.

## SKILL 12 — extract_expiry
Extrai validade e normaliza sem inventar dia quando só há MM/AAAA.

## SKILL 13 — extract_manufacture_date
Mantém fabricação separada de validade.

## SKILL 14 — count_visible_units
Conta somente unidades visualmente distinguíveis e retorna confiança.

## SKILL 15 — aggregate_same_lot_evidence
Agrega evidências do mesmo produto/lote com prevenção de duplicidade.

## SKILL 16 — detect_duplicate_photo
Usa hash exato e perceptual para suspeita de repetição.

## SKILL 17 — match_product
Compara esperado × observado com regras explícitas.

## SKILL 18 — match_lot
Comparação exata/conservadora de lote.

## SKILL 19 — match_quantity
Compara quantidades considerando múltiplas fotos e lotes.

## SKILL 20 — classify_expiry
Classifica validade: OK, crítica, vencida, desconhecida, inválida.

## SKILL 21 — calculate_field_confidence
Mantém confidence por produto/lote/validade/quantidade.

## SKILL 22 — require_manual_review
Centraliza regras que obrigam revisão.

## SKILL 23 — create_discrepancy
Cria divergência tipada e auditável.

## SKILL 24 — resolve_discrepancy
Registra decisão humana sem apagar valor original.

## SKILL 25 — build_exception_queue
Ordena itens que precisam de intervenção farmacêutica.

## SKILL 26 — approve_transfer
Valida pré-condições e autorização.

## SKILL 27 — post_transfer_to_stock
Gera movimentos por produto+lote+validade de modo idempotente.

## SKILL 28 — rollback_stock_posting
Reverte somente dentro das regras de negócio autorizadas e auditadas.

## SKILL 29 — update_fefo_index
Recalcula ordem FEFO após recebimento.

## SKILL 30 — expose_in_transit_stock
Disponibiliza transferência pendente como projeção separada, nunca como saldo físico.

## SKILL 31 — update_purchase_forecast
Atualiza previsão após recebimento aprovado sem dupla contagem.

## SKILL 32 — create_audit_event
Registra ator, ação, before/after, timestamp e correlation id.

## SKILL 33 — validate_state_transition
Impede transições inválidas da transferência.

## SKILL 34 — acquire_approval_lock
Protege aprovação concorrente.

## SKILL 35 — generate_idempotency_key
Impede dupla entrada da mesma transferência/item.

## SKILL 36 — reprocess_evidence
Reexecuta extração sem duplicar dados e mantendo histórico de versões.

## SKILL 37 — compare_ai_extraction_versions
Permite auditar mudança de provider/modelo/prompt.

## SKILL 38 — redact_sensitive_logs
Remove segredos e dados desnecessários dos logs.

## SKILL 39 — signed_evidence_access
Fornece acesso temporário/seguro às imagens quando a stack suportar.

## SKILL 40 — transfer_dashboard_metrics
Calcula indicadores de processo e qualidade.

## SKILL 41 — build_transfer_summary
Gera resumo: esperado, recebido, conforme, divergente, pendente.

## SKILL 42 — export_reconciliation_report
Gera relatório de conferência com documento, fotos, decisões e auditoria.

## SKILL 43 — fixture_real_report
Cria fixture baseada no formato real Ji-Paraná → Cacoal, sem depender de produção.

## SKILL 44 — mock_vision_provider
Retorna resultados determinísticos para testes.

## SKILL 45 — test_multiple_lots
Valida um produto com lotes diferentes e quantidades separadas.

## SKILL 46 — test_partial_photo
Valida que item encoberto vire revisão manual.

## SKILL 47 — test_double_approval
Garante que duas aprovações não dupliquem estoque.

## SKILL 48 — test_stock_rollback
Valida atomicidade quando postagem falha.

## SKILL 49 — test_rbac_transfer
Valida que somente perfis autorizados aprovem.

## SKILL 50 — transfer_health_check
Verifica parsers, provider de IA, fila/job e integração de estoque.
