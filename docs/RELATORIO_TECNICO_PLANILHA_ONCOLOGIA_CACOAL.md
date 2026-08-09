# Relatório técnico — Planilha de previsão mensal e estoque

## Arquivo analisado

- Original preservado: `C:\Users\henri\Downloads\02-TABELA_AUTOMATIZADA_PREVISAO_MENSAL_ESTOQUE.xlsx`
- Cópia de trabalho: `02-TABELA_AUTOMATIZADA_PREVISAO_MENSAL_ESTOQUE-COPIA-TRABALHO.xlsx`
- Formato: XLSX
- Tamanho: 5.938.166 bytes (aproximadamente 5,94 MB)
- Data de criação do original: 02/08/2026 20:31:38
- Última alteração do original: 02/08/2026 20:31:44
- Macros: não encontradas
- Conexões externas: não encontradas
- Cadeia de cálculo do Excel: presente

O arquivo original não foi alterado. A tentativa de importação completa pelo mecanismo de planilhas excedeu dez minutos. A inspeção foi concluída diretamente sobre a estrutura interna do XLSX, preservando o arquivo e permitindo identificar abas, dimensões, fórmulas, referências e erros. Por causa dessa limitação, os resultados numéricos ainda precisam ser reconciliados no Excel antes da migração definitiva.

## Estrutura encontrada

Foram identificadas 16 abas:

| Aba | Visibilidade | Dimensão | Função principal |
|---|---|---:|---|
| Aplicacoes | Visível | A1:U417 | Cadastro de tratamentos e previsão mensal de datas |
| Planilha1 | Visível | A1 | Aba vazia |
| Estoque | Visível | A1:AL225 | Consumo, saldo projetado e sugestão mensal de compra |
| Agosto a Junho | Visíveis | A1:G1431 em cada mês | Detalhamento mensal por paciente e medicamento |
| _Calculo | Oculta | A1:V24005 | Expansão das aplicações por ciclo e por mês |
| Cadastro_Estoque | Visível | A1:D135 | Cadastro manual do saldo atual por medicamento |

### Tabela estruturada

Existe uma tabela formal, `TabelaAplicacoes`, em `Aplicacoes!A5:U378`, com 21 campos:

- Plano
- Paciente
- Medicamento
- Início do tratamento
- Intervalo do ciclo em dias
- Dose por ciclo
- Unidade
- Quantidade de ciclos previstos
- Aplicações por ciclo
- Status
- Previsões mensais de agosto de 2026 a junho de 2027

### Campos principais por conjunto

**Aplicacoes:** plano, paciente, medicamento, início, intervalo, dose, unidade, ciclos, aplicações por ciclo e status.

**Abas mensais:** paciente, medicamento, quantidade de aplicações, dose total no mês, unidade, datas previstas e observações.

**Estoque:** medicamento, estoque atual, unidade, observações e, para cada mês, consumo, saldo após previsão e quantidade a comprar.

**Cadastro_Estoque:** medicamento, estoque atual, unidade e observações.

## Lógica identificada

1. A aba `Aplicacoes` recebe os dados manuais do tratamento.
2. As datas futuras são calculadas a partir da data inicial, do intervalo em dias, da quantidade de ciclos e do status ativo.
3. As fórmulas usam principalmente `AGGREGATE`, `DATE`, `EOMONTH`, `ROW`, `TEXT`, `IF` e `IFERROR` para localizar as ocorrências de cada mês.
4. A aba oculta `_Calculo` expande os tratamentos em aplicações individuais e calcula dose total por aplicação.
5. As abas mensais usam `INDEX` e `AGGREGATE` para extrair as aplicações do mês e calculam a demanda mensal.
6. A aba `Estoque` busca o saldo em `Cadastro_Estoque`, soma o consumo de cada mês com `SUMIFS`, calcula o saldo projetado e sugere compra por `MAX(0; demanda - saldo)`.
7. O saldo do mês seguinte incorpora a compra sugerida no mês anterior. Isso equivale a assumir que toda compra sugerida chega integralmente e a tempo, regra que precisa ser substituída por pedidos e recebimentos reais.

## Problemas e riscos encontrados

### Erros confirmados

- A aba oculta `_Calculo` contém **21.600 células com `#REF!`**.
- Foram identificadas **8.640 fórmulas estruturalmente quebradas**, a partir da linha 3006, referenciando `Aplicacoes!#REF!`.
- As 11 abas mensais somam **516 células com `#NUM!`**, principalmente na coluna de data prevista. As fórmulas pedem ao `AGGREGATE` uma ocorrência que já não existe e não possuem proteção adequada nessa parte do intervalo.
- Total de erros calculados identificados: **22.116 células**.

### Fragilidades de modelo

- Horizonte fixo de agosto/2026 a junho/2027; adicionar novos meses exige novas colunas e fórmulas.
- A tabela formal termina na linha 378, mas fórmulas consultam até a linha 1202 e a aba oculta se estende até a linha 24005.
- Datas mensais são concatenadas como texto, dificultando ordenação, auditoria e integração.
- Apenas `Aplicacoes` usa tabela estruturada; as demais áreas dependem de intervalos fixos.
- Não foram detectadas validações de dados nem regras de formatação condicional.
- A planilha calcula compra em unidade clínica, mas não modela de forma completa apresentação comercial, frascos, caixas, fator de conversão, lote, validade, FEFO e desperdício.
- Transferências, pedidos em trânsito, reservas, estoque de segurança e prazo de entrega não fazem parte do cálculo atual.
- A compra sugerida é tratada como entrada futura automática, sem confirmação de pedido ou recebimento.
- Não existe trilha de auditoria, controle de perfis ou separação por clínica na planilha.
- A aba `Planilha1` está vazia e deve ser ignorada na migração.

## Necessidades derivadas para o aplicativo

1. Substituir colunas mensais por registros individuais de aplicações com datas reais.
2. Importar inicialmente as abas `Aplicacoes` e `Cadastro_Estoque`.
3. Tratar as abas mensais, `Estoque` e `_Calculo` somente como fontes de reconciliação, não como dados mestres.
4. Criar mapeamento de colunas reutilizável para futuras planilhas GMED, Excel e CSV.
5. Validar obrigatórios, datas, unidades, status, medicamentos, duplicidades e sequência de ciclos antes da importação.
6. Separar posição de estoque de movimentação de estoque.
7. Controlar reservas por aplicação, lotes, validades, transferências, pedidos e recebimentos.
8. Calcular necessidade por paciente e aplicação e depois converter para apresentações comerciais.
9. Manter memória de cálculo auditável e exigir validação farmacêutica para dose, apresentação e compra.
10. Implementar autenticação, perfis, `clinic_id`, RLS e auditoria antes de utilizar dados reais.

## Proposta de arquitetura

### Front-end

- Aplicativo responsivo em português do Brasil no Lovable.
- Módulos: painel, agenda, pacientes, tratamentos, medicamentos, apresentações, estoque, transferências, pedidos, lista de compras, importações, alertas, relatórios, usuários, permissões e auditoria.

### Back-end e banco de dados

- Lovable Cloud/Supabase com banco PostgreSQL relacional.
- Separação obrigatória por clínica/unidade por meio de `clinic_id` e políticas RLS.
- Armazenamento privado para planilhas e documentos.
- Funções de servidor para importação, cálculo de demanda e geração da lista de compras.
- Regras de cálculo versionadas; toda alteração deve registrar usuário, data, valores anterior e posterior.

### Modelo de dados inicial

- clínicas/unidades, usuários, perfis e permissões;
- pacientes;
- medicamentos e apresentações comerciais;
- tratamentos, ciclos e aplicações;
- posições e movimentações de estoque;
- lotes, validades e reservas;
- transferências e itens de transferência;
- pedidos, itens e recebimentos;
- importações, modelos de mapeamento e inconsistências;
- sugestões de compra, memória de cálculo, aprovações e justificativas;
- alertas e auditoria.

## Plano de migração

1. Preservar o arquivo original e trabalhar somente com a cópia.
2. Corrigir ou excluir da migração os intervalos com `#REF!` e `#NUM!`.
3. Criar dicionários padronizados de medicamentos, unidades e apresentações.
4. Importar `Cadastro_Estoque` como posição inicial de estoque, com data de referência.
5. Importar `Aplicacoes` para tratamentos e aplicações normalizadas.
6. Recalcular as datas no novo motor; não importar como verdade definitiva as datas concatenadas das abas mensais.
7. Comparar, medicamento por medicamento e mês por mês, os resultados novos com `Agosto` a `Junho` e com `Estoque`.
8. Apresentar todas as divergências ao farmacêutico responsável.
9. Executar os dez testes de aceitação descritos no prompt com dados fictícios.
10. Liberar um piloto para Cacoal somente depois da validação de segurança e dos cálculos.

## Primeira implementação recomendada

O primeiro módulo deve ser **Importações e validação**, porque ele cria a base confiável para todas as etapas seguintes. A primeira versão deve incluir:

- seleção da origem do arquivo;
- upload de XLSX/CSV;
- detecção e mapeamento de colunas;
- salvamento de modelos de mapeamento;
- prévia sem efetivar a importação;
- classificação em válido, revisão, erro, duplicado ou rejeitado;
- relatório de inconsistências;
- importação separada de aplicações e posição de estoque;
- auditoria da importação.

Depois: modelo normalizado, motor de demanda, memória de cálculo e lista de compras.

## Pontos que exigem validação farmacêutica

- Significado exato de “aplicações por ciclo” e risco de multiplicação duplicada da dose.
- Critérios para tratamento ativo, suspenso, cancelado e guia autorizada.
- Conversão entre mg, mL, frasco, ampola, comprimido e caixa.
- Regras de arredondamento, compartilhamento de frascos e desperdício aceitável.
- Escolha de apresentações comerciais e fabricantes equivalentes.
- Estoque de segurança e prazo mínimo por medicamento.
- Uso de transferências e pedidos em trânsito conforme a primeira data de necessidade.
- FEFO, validade mínima e reserva por paciente.
- Fórmulas para mg/m², mg/kg, AUC e limites de dose.
- Quem pode aprovar ajustes de estoque, dose e quantidade de compra.

## Perguntas obrigatórias para a próxima validação

1. Quais regras de cálculo ou campos precisam ser validados pelo farmacêutico responsável?
2. Quais integrações já possuem acesso técnico, API, relatório ou arquivo de exemplo disponível?
3. Quais resultados foram comparados com a planilha original?
4. Quais inconsistências impedem a geração segura da lista de compras?
5. Qual será a próxima etapa objetiva do desenvolvimento?
