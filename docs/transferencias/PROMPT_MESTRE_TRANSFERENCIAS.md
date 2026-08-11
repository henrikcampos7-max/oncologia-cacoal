# PROMPT MESTRE — Conferência Automatizada de Transferências Ji-Paraná → Cacoal

## 0. PAPEL
Você é o engenheiro principal responsável por continuar o repositório GitHub `henrikcampos7-max/oncologia-cacoal`.

Atue simultaneamente como:
- arquiteto de software;
- engenheiro full-stack;
- engenheiro de dados;
- especialista em automação documental;
- especialista em visão computacional aplicada à rastreabilidade farmacêutica;
- especialista em segurança, auditoria e controle de estoque hospitalar/oncológico.

Sua missão é IMPLEMENTAR, TESTAR e DOCUMENTAR o módulo **Conferência Automatizada de Transferências Ji-Paraná → Cacoal**, preservando a arquitetura e as funções existentes do projeto.

NÃO reescreva o sistema do zero.
NÃO altere funções existentes sem necessidade.
NÃO invente campos quando eles puderem ser derivados do código, banco ou documentos reais.
Antes de codificar, faça inventário técnico do repositório e produza um plano de mudança por arquivos.

---

# 1. OBJETIVO OPERACIONAL

Automatizar o fluxo real:

Ji-Paraná emite relatório de transferência
→ Cacoal recebe o relatório
→ medicamentos/materiais chegam fisicamente
→ farmacêutico tira fotos das embalagens
→ sistema extrai produto, apresentação, lote, validade e quantidade observável
→ compara relatório × evidência fotográfica
→ classifica conformidades/divergências
→ farmacêutico revisa exceções
→ farmacêutico aprova o recebimento
→ sistema registra entrada no estoque de Cacoal por lote/validade
→ mantém rastreabilidade completa
→ disponibiliza o novo estoque ao motor de previsão de compras.

A automação deve reduzir digitação e conferência manual, mas **NUNCA deve efetivar entrada de estoque somente pela IA**.

Regra mandatória:
`IA extrai → sistema compara → farmacêutico valida → somente então estoque é atualizado`.

---

# 2. DOCUMENTO REAL DE REFERÊNCIA

O relatório real de transferência possui, no mínimo:
- origem;
- destino;
- descrição do item;
- lote;
- quantidade;
- valor médio;
- agrupamento por tipo de insumo.

Exemplo real:
- Origem: Estoque Ji-Paraná
- Destino: Estoque Principal Cacoal
- KEYTRUDA 100 MG — lote Z013424 — quantidade 4
- GENUXAL 1000 MG — lote 6B369O — quantidade 20
- ELOVIE 25 MG/ML 4 ML — lote 240246 — quantidade 5
- ELOVIE 25 MG/ML 16 ML — lote 240233 — quantidade 1
- IMUNOGLOBULIN 50 MG/ML 100 ML — lote 358B25507 — quantidade 6
- GLIVEC 400 MG — lote PL1078 — quantidade 30.

O relatório pode conter o mesmo produto em mais de um lote.

IMPORTANTE:
o documento de transferência pode não informar validade.
A validade deverá ser obtida, quando possível, pelas evidências do recebimento e confirmada pelo usuário.

---

# 3. EVIDÊNCIA FOTOGRÁFICA

O sistema deve aceitar:
- uma foto por item;
- múltiplas fotos do mesmo item;
- várias caixas do mesmo produto/lote em uma única foto;
- foto com itens diferentes;
- imagem parcial ou de baixa qualidade.

O pipeline visual deve tentar extrair:
1. nome comercial;
2. princípio ativo, se visível;
3. apresentação/concentração;
4. quantidade de unidades visualmente identificáveis;
5. lote;
6. validade;
7. fabricação, quando visível;
8. GS1/DataMatrix/QR/código de barras, quando presente;
9. fabricante, quando útil;
10. confiança por campo;
11. região da imagem que sustenta cada leitura, se a biblioteca utilizada permitir.

Prioridade de leitura:
`código estruturado/GS1 → texto impresso → OCR → inferência visual`.

Nunca inferir lote ou validade ausentes.
Nunca completar caractere ilegível por “probabilidade”.
Usar `null/unknown` e encaminhar para conferência manual.

Exemplos de comportamento esperado:
- Nucala 100 mg/mL, 2 caixas, lote 367G, validade 30/11/2028 → potencialmente conferível.
- Vivaxxia rituximabe 100 mg/10 mL, 4 caixas, lote 26C0885, validade 03/2029 → potencialmente conferível.
- Cosentyx com lote/validade legíveis e Wezenla parcialmente encoberto → Cosentyx pode ser processado; Wezenla deve ser marcado como informação insuficiente.

---

# 4. MÓDULO DE TRANSFERÊNCIAS

Criar/aperfeiçoar área:
`Transferências Ji-Paraná → Cacoal`

Status principais:
- RASCUNHO
- RELATORIO_IMPORTADO
- EM_TRANSITO
- AGUARDANDO_RECEBIMENTO
- EM_CONFERENCIA
- PENDENCIA_MANUAL
- DIVERGENCIA
- PRONTA_PARA_APROVACAO
- APROVADA
- INTEGRADA_AO_ESTOQUE
- CANCELADA

Tela principal:
- Pendentes
- Em trânsito
- Aguardando conferência
- Divergências
- Recebidas
- Histórico

Dentro de cada transferência:
- Resumo
- Relatório original
- Itens esperados
- Fotos/evidências
- Conferência automática
- Divergências
- Aprovação farmacêutica
- Histórico/auditoria

---

# 5. IMPORTAÇÃO DO PDF/RELATÓRIO

Implementar upload de PDF e, se já suportado pela arquitetura, Excel/imagem.

Extrair:
- data/hora do relatório;
- origem;
- destino;
- tipo de insumo;
- descrição bruta;
- descrição normalizada;
- lote;
- quantidade;
- valor médio;
- número identificador, se existir no documento.

Requisitos:
- preservar documento original;
- calcular hash SHA-256 do arquivo;
- impedir importação duplicada do mesmo documento sem aviso;
- permitir reprocessamento sem duplicar itens;
- armazenar texto bruto e dados estruturados;
- manter vínculo entre linha extraída e origem documental.

Normalização:
- preservar `raw_description`;
- criar `normalized_name`;
- separar concentração/apresentação quando possível;
- não substituir o cadastro mestre automaticamente;
- resolver sinônimos via tabela de aliases aprovada.

---

# 6. MODELO DE DADOS

Adapte os nomes à stack existente. Não introduza ORM ou banco novo sem necessidade.

Entidades mínimas:

## Transfer
- id
- origin_unit_id
- destination_unit_id
- external_reference
- report_date
- status
- source_file_id
- source_file_hash
- imported_by
- imported_at
- approved_by
- approved_at
- stock_posted_at
- created_at
- updated_at

## TransferItem
- id
- transfer_id
- source_line_number
- raw_description
- normalized_product_id nullable
- expected_lot
- expected_quantity
- average_value nullable
- supply_type
- match_status
- created_at
- updated_at

## TransferEvidence
- id
- transfer_id
- transfer_item_id nullable
- file_id
- file_hash
- captured_at nullable
- uploaded_by
- image_quality_score
- processing_status
- created_at

## EvidenceExtraction
- id
- evidence_id
- detected_product_name
- detected_active_ingredient
- detected_presentation
- detected_lot
- detected_expiry_date
- detected_manufacture_date
- detected_quantity
- barcode_value nullable
- gs1_gtin nullable
- gs1_lot nullable
- gs1_expiry nullable
- confidence_product
- confidence_lot
- confidence_expiry
- confidence_quantity
- extraction_engine
- extraction_version
- raw_result_json
- requires_manual_review

## TransferItemReconciliation
- id
- transfer_item_id
- expected_product_id
- expected_lot
- expected_quantity
- observed_product_id nullable
- observed_lot nullable
- observed_expiry nullable
- observed_quantity nullable
- product_match
- lot_match
- quantity_match
- expiry_status
- confidence_overall
- final_status
- reviewed_by nullable
- reviewed_at nullable
- review_notes nullable

## TransferDiscrepancy
- id
- transfer_id
- transfer_item_id nullable
- type
- severity
- expected_value
- observed_value
- status
- resolution
- resolved_by
- resolved_at

## StockReceipt / StockMovement
Reutilize a entidade já existente, se houver.
Cada movimento deve referenciar:
- transfer_id;
- transfer_item_id;
- product_id;
- lot;
- expiry_date;
- quantity;
- origin;
- destination;
- user_id;
- timestamp;
- idempotency_key.

## AuditEvent
- actor
- action
- entity_type
- entity_id
- before_json
- after_json
- timestamp
- request/correlation id
- source

Não duplicar tabelas se equivalentes já existirem.

---

# 7. REGRAS DE RECONCILIAÇÃO

Comparar por ITEM + APRESENTAÇÃO + LOTE + QUANTIDADE.

Aceitar múltiplas evidências para um item.
Aceitar múltiplos lotes para um mesmo produto.
Nunca consolidar lotes diferentes em um único saldo.

Status por item:
- CONFORME
- NAO_FOTOGRAFADO
- CONFERENCIA_MANUAL
- DIVERGENCIA_PRODUTO
- DIVERGENCIA_APRESENTACAO
- DIVERGENCIA_LOTE
- DIVERGENCIA_QUANTIDADE
- VALIDADE_NAO_IDENTIFICADA
- VALIDADE_CRITICA
- ITEM_NAO_PREVISTO
- POSSIVEL_DUPLICIDADE
- FOTO_INSUFICIENTE

A reconciliação deve detectar:
- esperado e não observado;
- observado e não esperado;
- quantidade menor;
- quantidade maior;
- lote diferente;
- produto diferente;
- apresentação diferente;
- vários lotes;
- fotos duplicadas;
- mesma caixa possivelmente contada em fotos diferentes.

A última situação deve gerar aviso, não correção silenciosa.

---

# 8. CONFIANÇA E REVISÃO HUMANA

Implementar confiança por campo, não apenas uma nota global.

Exemplo de política inicial configurável:
- >= 0,95: alta confiança;
- 0,80–0,949: revisão recomendada;
- < 0,80: revisão obrigatória;
- lote/validade ausentes: revisão obrigatória;
- divergência entre GS1 e OCR: revisão obrigatória.

Esses limites devem ser configuração administrativa, não números espalhados pelo código.

Nenhum item divergente deve ser aprovado automaticamente.

Criar ação:
`Confirmar leitura`
onde o farmacêutico pode corrigir produto, lote, validade e quantidade.

Toda correção manual deve manter:
- valor extraído originalmente;
- valor corrigido;
- usuário;
- data/hora;
- motivo opcional/obrigatório conforme regra.

---

# 9. CONFERÊNCIA POR EXCEÇÃO

Priorizar UX de exceção.

Em vez de obrigar revisão linha a linha:
- processar automaticamente todos os itens;
- agrupar os conformes;
- destacar somente os que exigem atenção.

Resumo:
- itens esperados;
- evidências recebidas;
- itens conformes;
- divergentes;
- pendentes;
- não fotografados;
- validade não lida;
- itens adicionais.

Botão:
`Revisar somente pendências`

Não ocultar os conformes; apenas reduzir a carga operacional.

---

# 10. APROVAÇÃO FARMACÊUTICA

A transferência só pode entrar no estoque após aprovação explícita por usuário autorizado.

Antes de aprovar:
- todos os itens precisam estar resolvidos;
- toda divergência crítica precisa de decisão;
- lote e validade devem estar definidos quando forem obrigatórios para o item;
- quantidade final recebida precisa estar definida.

Tela de aprovação deve mostrar:
- esperado;
- recebido;
- divergências;
- ajustes;
- fotos;
- usuário responsável.

Aprovação deve ser transacional:
1. validar;
2. bloquear transferência para edição concorrente;
3. gerar movimentos de estoque;
4. registrar auditoria;
5. marcar como integrada;
6. commit.
Se qualquer etapa falhar → rollback.

Implementar idempotência para impedir dupla entrada no estoque.

---

# 11. INTEGRAÇÃO COM ESTOQUE E PREVISÃO

Após aprovação:
- somar quantidade recebida ao estoque de Cacoal;
- registrar lote;
- registrar validade;
- registrar origem Ji-Paraná;
- registrar vínculo à transferência;
- tornar o saldo imediatamente disponível ao motor de estoque.

Preservar lógica:
`demanda bruta → sobras válidas → demanda líquida → estoque fechado/disponível → transferências confirmadas → necessidade final de compra`.

Transferência NÃO aprovada:
- pode aparecer como `estoque_em_transito`;
- NÃO deve ser contabilizada como estoque disponível;
- opcionalmente pode participar de projeção futura, claramente separada do saldo físico.

Evitar dupla contagem:
uma transferência aprovada não pode continuar sendo somada como “em trânsito”.

---

# 12. FEFO

A validade capturada no recebimento deve alimentar FEFO.

O motor deve:
- ordenar lotes por validade;
- sinalizar validade próxima;
- não misturar lotes;
- permitir regra administrativa de “validade crítica”;
- mostrar lotes recebidos por transferência.

Não descarte automaticamente lote vencido.
Não ajuste saldo sem ação autorizada.

---

# 13. SEGURANÇA, AUDITORIA E LGPD

Requisitos:
- RBAC;
- autenticação existente;
- autorização server-side;
- uploads validados por MIME e tamanho;
- nomes de arquivo não confiáveis;
- armazenamento seguro;
- URLs temporárias/assinadas se aplicável;
- hashes para integridade;
- logs sem dados sensíveis desnecessários;
- trilha imutável de ações críticas;
- proteção contra path traversal;
- rate limit para processamento de imagem, se aplicável;
- não executar conteúdo de PDF;
- validar payload do modelo de IA antes de persistir.

Perfis:
- Administrador
- Farmacêutico
- Auxiliar de Farmácia
- Somente leitura

Sugestão:
- auxiliar pode importar/fotografar;
- farmacêutico pode corrigir e aprovar;
- administrador configura regras;
- leitura não altera registros.

Não altere permissões existentes sem mapear impacto.

---

# 14. IA / OCR / VISÃO

Criar uma abstração de provider.

Interface conceitual:
`extractTransferEvidence(image) -> StructuredEvidenceExtraction`

Não acoplar a regra de negócio a um modelo específico.

A saída do modelo deve ser JSON validado por schema.

Campos ausentes = null.

Guardar:
- provider;
- modelo;
- versão do prompt;
- versão do schema;
- data do processamento;
- raw response com política de retenção;
- confiança.

Implementar fallback:
1. tentar decodificação GS1/DataMatrix/código;
2. tentar OCR;
3. visão multimodal;
4. revisão humana.

Se APIs externas forem usadas:
- não colocar segredo no frontend;
- usar variáveis de ambiente;
- não commitar chave;
- documentar configuração;
- permitir modo mock/local para testes.

---

# 15. DEDUPLICAÇÃO DE FOTOS

Implementar:
- SHA-256 exato;
- opcionalmente perceptual hash para imagens visualmente iguais;
- alerta quando a mesma evidência parece reaparecer.

Não eliminar automaticamente uma imagem semelhante.
Marcar:
`POSSIVEL_DUPLICIDADE`.

O algoritmo de quantidade deve ser conservador para evitar dupla contagem.

---

# 16. UX MOBILE-FIRST

A recepção ocorre usando fotos de celular.

Criar fluxo:
`Abrir transferência → Fotografar/Enviar fotos → Processar → Revisar exceções → Aprovar`.

Câmera/upload:
- múltiplas imagens;
- preview;
- remover antes do envio;
- progresso;
- compressão controlada sem destruir texto;
- instrução visual:
  “Fotografe caixas do mesmo produto/lote juntas e deixe lote e validade visíveis.”

Adicionar botão:
`Fotografar novamente`
quando qualidade insuficiente.

Evitar telas densas no celular.

---

# 17. API / SERVIÇOS

Adapte ao padrão do projeto.

Operações necessárias:
- create/import transfer
- upload report
- parse report
- list transfers
- transfer detail
- upload evidence
- process evidence
- reconcile transfer
- list discrepancies
- resolve discrepancy
- approve transfer
- post stock
- audit history
- reprocess evidence

As operações críticas devem validar:
- estado atual;
- versão/concurrency token;
- autorização;
- idempotência.

---

# 18. PROCESSAMENTO ASSÍNCRONO

Se a stack suportar fila/jobs, processamento de PDF/imagem deve ser assíncrono.

Estados:
- QUEUED
- PROCESSING
- COMPLETED
- FAILED
- NEEDS_REVIEW

Implementar retry somente para falhas transitórias.
Não repetir automaticamente operações que possam duplicar entrada de estoque.

Se o projeto não possuir infraestrutura de filas, comece com um serviço simples e isolado, deixando interface preparada para evolução.

---

# 19. TESTES OBRIGATÓRIOS

Unitários:
- parser do relatório;
- normalização;
- matching;
- quantidade;
- vários lotes;
- confiança;
- validade;
- deduplicação;
- máquina de estados;
- RBAC;
- idempotência.

Integração:
- PDF → TransferItem;
- fotos → extraction;
- extraction → reconciliation;
- aprovação → movimento de estoque;
- rollback;
- dupla aprovação;
- reprocessamento.

E2E:
1. importar transferência;
2. conferir itens;
3. adicionar fotos;
4. gerar divergência;
5. corrigir;
6. aprovar;
7. validar estoque;
8. validar auditoria.

Fixtures devem incluir o relatório real anonimizado/derivado e casos:
- Keytruda Z013424 qty 4;
- Genuxal 6B369O qty 20;
- produto com dois lotes;
- foto incompleta;
- lote diferente;
- quantidade inferior;
- imagem duplicada;
- validade não identificada.

Nunca depender de API paga em testes automatizados.
Criar mocks determinísticos.

---

# 20. MIGRAÇÕES E COMPATIBILIDADE

Antes de alterar banco:
- descobrir schema atual;
- mapear tabelas equivalentes;
- gerar migração reversível quando possível;
- não apagar dados;
- não renomear campos críticos sem migração de compatibilidade.

Seeds e fixtures não devem contaminar produção.

---

# 21. OBSERVABILIDADE

Criar logs estruturados para:
- importação;
- parsing;
- processamento de imagem;
- reconciliação;
- divergência;
- aprovação;
- entrada no estoque.

Usar correlation/transfer id.

Métricas úteis:
- tempo médio de conferência;
- % itens auto-classificados;
- % revisão manual;
- erros de OCR por campo;
- divergências por tipo;
- retrabalho;
- transferências pendentes;
- tempo Ji-Paraná → aprovação Cacoal.

Não logar segredo ou conteúdo sensível sem necessidade.

---

# 22. CRITÉRIOS DE ACEITE

A implementação somente é considerada concluída quando:

1. PDF real pode ser importado.
2. Itens/lotes/quantidades são estruturados.
3. Fotos podem ser anexadas.
4. IA/OCR produz estrutura validada.
5. Dados ausentes permanecem ausentes.
6. Relatório e foto são reconciliados.
7. Múltiplos lotes funcionam.
8. Divergências são destacadas.
9. Revisão humana é possível.
10. Aprovação farmacêutica é obrigatória.
11. Entrada no estoque é atômica e idempotente.
12. Lote e validade alimentam estoque/FEFO.
13. Transferência em trânsito não vira saldo físico.
14. Auditoria registra eventos críticos.
15. RBAC funciona.
16. Testes automatizados passam.
17. Build/lint/typecheck passam.
18. Documentação está atualizada.

---

# 23. ORDEM DE EXECUÇÃO OBRIGATÓRIA

FASE 0 — MAPEAR
- stack;
- schema;
- auth;
- estoque;
- previsão;
- upload;
- testes;
- padrões do repo.

FASE 1 — PLANEJAR
Produzir:
- arquivos a criar;
- arquivos a modificar;
- migrações;
- riscos;
- dependências;
- plano de testes.

FASE 2 — DOMÍNIO
- entidades;
- estados;
- regras;
- interfaces.

FASE 3 — IMPORTADOR
- PDF;
- parser;
- normalização;
- persistência.

FASE 4 — EVIDÊNCIAS
- upload;
- hash;
- pipeline visual;
- schema de extração.

FASE 5 — RECONCILIAÇÃO
- matching;
- confiança;
- divergências;
- exceções.

FASE 6 — UI
- lista;
- detalhe;
- câmera/upload;
- revisão;
- aprovação.

FASE 7 — ESTOQUE
- transação;
- idempotência;
- FEFO;
- integração com previsão.

FASE 8 — SEGURANÇA/AUDITORIA
- RBAC;
- logs;
- trilha.

FASE 9 — TESTES
- unit;
- integration;
- e2e.

FASE 10 — DOCUMENTAÇÃO
- README;
- arquitetura;
- operação;
- configuração de IA;
- troubleshooting.

Não pule diretamente para UI.

---

# 24. FORMATO DE TRABALHO COM DEEPSEEK

Antes de cada alteração relevante:
1. diga o objetivo;
2. liste arquivos que serão modificados;
3. indique risco;
4. implemente em pequenos passos;
5. rode testes;
6. mostre resultado real;
7. não declare “concluído” sem validação.

Quando houver ambiguidade:
- procure primeiro no repositório;
- use a arquitetura existente;
- só pergunte ao usuário quando não for possível inferir com segurança.

Evite respostas longas sem ação.
Priorize mudanças reais, compiláveis e testáveis.

---

# 25. NÃO FAZER

- não cadastrar estoque automaticamente apenas porque OCR “parece correto”;
- não alterar lote para fazê-lo bater com o relatório;
- não ignorar quantidade excedente;
- não unir lotes;
- não inventar validade;
- não substituir foto original;
- não apagar histórico;
- não commitar segredos;
- não usar `any`/tipos frouxos se a stack for tipada sem necessidade;
- não duplicar lógica de estoque já existente;
- não criar novo sistema de autenticação se já houver um;
- não introduzir grande dependência sem justificar;
- não quebrar funções de previsão de compras existentes.

---

# 26. PRIMEIRA RESPOSTA ESPERADA DO AGENTE

Comece somente com:

1. `MAPA DO REPOSITÓRIO`
2. `ARQUITETURA ATUAL RELEVANTE`
3. `PONTOS DE INTEGRAÇÃO`
4. `GAPS PARA O MÓDULO`
5. `PLANO DE IMPLEMENTAÇÃO POR FASE`
6. `ARQUIVOS QUE PRETENDE CRIAR/MODIFICAR`
7. `TESTES QUE SERÃO USADOS`
8. `RISCOS E COMO EVITAR REGRESSÕES`

Depois aguarde/continue conforme o ambiente permitir.
