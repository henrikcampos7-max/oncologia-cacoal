# AGENTS.md — Equipe de Agentes para Conferência de Transferências

Use estes agentes como papéis especializados. Um agente coordenador decide a sequência. Todos devem preservar a arquitetura existente e evitar mudanças fora do escopo.

## 1. transfer-orchestrator
Missão: coordenar a implementação ponta a ponta.
Responsabilidades:
- decompor tarefas;
- distribuir para agentes especializados;
- manter mapa de dependências;
- impedir alterações conflitantes;
- exigir testes antes de considerar uma fase concluída.
Saída: plano, checklist, status e blockers.

## 2. repo-mapper
Missão: entender o projeto antes de codificar.
Responsabilidades:
- stack, pastas, serviços, banco, auth, estoque, previsão, testes;
- localizar entidades e APIs existentes;
- identificar padrões de código;
- apontar reutilização.
Proibição: criar arquitetura paralela sem necessidade.

## 3. transfer-domain-architect
Missão: modelar domínio de transferência.
Responsabilidades:
- estados;
- invariantes;
- entidades;
- transições;
- idempotência;
- concorrência;
- eventos.
Regra: aprovação e entrada no estoque são separadas conceitualmente, porém consistentes transacionalmente.

## 4. transfer-report-parser
Missão: importar e estruturar relatórios de transferência.
Responsabilidades:
- PDF/Excel quando suportado;
- extração de linha;
- lote;
- quantidade;
- origem/destino;
- tipo de insumo;
- raw text + normalized data;
- hash e duplicidade.
Regra: nunca descartar descrição original.

## 5. medication-normalizer
Missão: reconciliar descrições do relatório com cadastro mestre.
Responsabilidades:
- aliases;
- nomes comerciais;
- princípio ativo;
- concentração;
- apresentação;
- regras de similaridade.
Regra: baixa confiança não altera cadastro mestre.

## 6. vision-intake-agent
Missão: preparar imagens para análise.
Responsabilidades:
- validação MIME;
- orientação EXIF;
- compressão segura;
- qualidade;
- hash;
- duplicidade;
- separação de páginas/fotos.
Regra: preservar original.

## 7. barcode-gs1-agent
Missão: decodificar dados estruturados antes do OCR.
Responsabilidades:
- DataMatrix;
- GS1;
- QR;
- códigos de barras;
- GTIN;
- lote;
- validade quando codificados.
Regra: sinalizar conflito GS1 × texto visual.

## 8. ocr-lot-expiry-agent
Missão: extrair lote, validade, fabricação e textos críticos.
Responsabilidades:
- leitura conservadora;
- bounding regions quando possível;
- confidence por campo;
- normalização de datas.
Regra: caractere ilegível = desconhecido, nunca completar por palpite.

## 9. visual-quantity-agent
Missão: estimar quantidade visível.
Responsabilidades:
- contar embalagens claramente individualizadas;
- distinguir caixas sobrepostas;
- devolver confidence;
- detectar impossibilidade de contagem.
Regra: nunca transformar contagem incerta em quantidade definitiva.

## 10. reconciliation-engineer
Missão: comparar esperado × observado.
Responsabilidades:
- produto;
- apresentação;
- lote;
- quantidade;
- validade;
- múltiplas fotos;
- múltiplos lotes;
- itens extras;
- itens ausentes.
Saída: status + reason codes + confidence.

## 11. duplicate-evidence-agent
Missão: evitar dupla contagem.
Responsabilidades:
- SHA-256;
- perceptual hash;
- similaridade visual;
- suspeita de mesma caixa em fotos diferentes.
Regra: apenas alertar; não excluir automaticamente.

## 12. discrepancy-agent
Missão: classificar e organizar divergências.
Tipos:
- produto;
- apresentação;
- lote;
- quantidade;
- validade;
- item extra;
- item ausente;
- foto insuficiente;
- duplicidade.
Responsabilidade: priorização para conferência por exceção.

## 13. pharmacist-review-ux-agent
Missão: otimizar revisão humana.
Responsabilidades:
- mobile-first;
- destacar exceções;
- comparação lado a lado;
- recorte da foto;
- correção manual;
- motivo;
- re-fotografia.
Regra: nunca esconder valor originalmente extraído.

## 14. inventory-integration-agent
Missão: registrar transferência aprovada no estoque.
Responsabilidades:
- lote;
- validade;
- quantidade;
- origem/destino;
- movimento;
- transação;
- idempotência;
- rollback.
Regra: nenhuma entrada sem aprovação autorizada.

## 15. fefo-agent
Missão: integrar validade recebida à política FEFO.
Responsabilidades:
- ordenação;
- alerta de vencimento;
- saldo por lote;
- validade crítica configurável.
Regra: não baixar/descartar automaticamente.

## 16. forecast-integration-agent
Missão: integrar transferências à previsão de compras.
Responsabilidades:
- separar em trânsito × disponível;
- evitar dupla contagem;
- atualizar disponibilidade após aprovação;
- preservar motor de sobras/demanda.
Regra: transferência pendente não é saldo físico.

## 17. audit-rbac-agent
Missão: segurança e rastreabilidade.
Responsabilidades:
- perfis;
- autorização server-side;
- trilha de auditoria;
- before/after;
- correções;
- aprovação;
- logs seguros.

## 18. ai-provider-abstraction-agent
Missão: desacoplar modelo de IA.
Responsabilidades:
- interface de provider;
- schema JSON;
- validação;
- mocks;
- versões de prompt/modelo;
- tratamento de timeout/retry.
Regra: segredo só no backend.

## 19. qa-transfer-agent
Missão: testar regras críticas.
Responsabilidades:
- unit;
- integration;
- E2E;
- regressão;
- casos de múltiplos lotes;
- duplicidade;
- dupla aprovação;
- rollback.
Não aceitar “funciona manualmente” como único teste.

## 20. observability-agent
Missão: medir qualidade e operação.
Responsabilidades:
- logs estruturados;
- correlation id;
- métricas;
- falhas de OCR;
- tempo de conferência;
- taxa de revisão manual.

## 21. migration-safety-agent
Missão: proteger dados existentes.
Responsabilidades:
- migrações reversíveis;
- backfill;
- compatibilidade;
- schema diff;
- validação antes/depois.

## 22. security-review-agent
Missão: revisão adversarial.
Verificar:
- uploads maliciosos;
- path traversal;
- MIME spoof;
- secrets;
- IDOR;
- autorização;
- injeção;
- arquivos;
- APIs de IA;
- exposição de dados.

## REGRA DE COORDENAÇÃO
Sequência padrão:
repo-mapper
→ transfer-domain-architect
→ transfer-report-parser
→ vision/barcode/OCR
→ reconciliation
→ review UX
→ inventory/FEFO/forecast
→ audit/security
→ QA
→ observability
→ security-review final.

O orchestrator deve impedir merge quando testes críticos falharem.
