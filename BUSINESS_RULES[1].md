# BUSINESS_RULES.md

## 1. Estrutura lógica da demanda
O cálculo deve respeitar a cadeia:

Demanda bruta
→ identificar sobras reais disponíveis
→ validar estabilidade da sobra
→ validar possibilidade de reutilização
→ verificar paciente seguinte e data
→ alocar sobra válida
→ calcular demanda líquida
→ consultar estoque fechado/disponível
→ calcular frascos/apresentações necessários
→ projetar nova sobra
→ verificar aproveitamento futuro
→ calcular necessidade final de compra

## 2. Paciente → consumo individual
Para cada paciente o sistema deve determinar:
- tratamento/protocolo;
- medicamento;
- dose necessária;
- datas ou frequência;
- ocorrências no período;
- quantidade total prevista no período.

## 3. Medicamento → consumo consolidado
A demanda mensal de um medicamento é a soma das necessidades dos pacientes elegíveis no período.

Não misturar cálculo individual com consolidação.

## 4. Demanda bruta
Quantidade total necessária antes de considerar:
- estoque;
- sobras;
- transferências;
- compras.

## 5. Sobras
Cada sobra deve ter, quando aplicável:
- medicamento;
- apresentação;
- quantidade remanescente;
- unidade;
- lote;
- origem;
- data/hora de abertura ou manipulação;
- data/hora limite de estabilidade;
- condição de armazenamento;
- status;
- paciente/procedimento de origem;
- paciente/procedimento que recebeu reaproveitamento;
- usuário responsável.

## 6. Sobra real x sobra projetada
Manter conceitos separados.

### Sobra real
Existe fisicamente e foi registrada após utilização/manipulação.

### Sobra projetada
É estimativa matemática gerada pelo planejamento futuro.

Nunca somar automaticamente sobra projetada ao estoque físico.

## 7. Reutilização de sobra
Uma sobra somente pode reduzir demanda se:
- estiver registrada como real quando o cálculo for operacional;
- estiver dentro da estabilidade válida;
- tiver condição de armazenamento válida;
- for compatível com a apresentação/regra aplicável;
- não tiver sido consumida ou descartada;
- puder ser rastreada.

## 8. FEFO para sobras
Quando houver mais de uma sobra válida e tecnicamente equivalente, priorizar a que tiver menor tempo restante de validade/estabilidade, salvo regra operacional configurada em contrário.

## 9. Rastreabilidade paciente A → paciente B
Se uma sobra originada no atendimento do paciente A for utilizada no paciente B, registrar vínculo entre origem e destino sem substituir os registros históricos.

## 10. Demanda líquida
Demanda líquida = demanda bruta - sobras válidas efetivamente alocáveis.

Não permitir resultado negativo.

## 11. Estoque
Estoque deve ser separado de demanda e de sobra.

Considerar categorias configuráveis como:
- estoque físico;
- estoque disponível;
- reservado;
- bloqueado;
- quarentena;
- vencido;
- transferência em trânsito.

Somente categorias autorizadas reduzem necessidade de compra.

## 12. Apresentações e frascos
Após a demanda líquida e estoque aplicável, converter necessidade em número de apresentações/frascos utilizando arredondamento adequado à apresentação cadastrada.

Registrar eventual nova sobra projetada.

## 13. Compra
Necessidade final de compra deve ser derivada do motor, e não digitada como substituta do cálculo.

Estrutura conceitual:
necessidade operacional
- estoque utilizável
- transferências confirmadas aplicáveis
+ estoque de segurança/configurações autorizadas
= necessidade de aquisição

A fórmula definitiva deve ser parametrizável conforme política institucional.

## 14. Transferências Ji-Paraná → Cacoal
A importação de relatório de transferência deve:
- validar duplicidade;
- identificar medicamento/apresentação;
- identificar quantidade;
- registrar origem;
- registrar data;
- manter arquivo ou referência de origem;
- gerar movimento auditável;
- refletir no estoque somente após regra de confirmação definida.

## 15. Auditoria
Alterações críticas devem manter:
- usuário;
- data/hora;
- ação;
- valor anterior;
- valor novo;
- entidade afetada;
- origem da alteração.

Evitar exclusão física de registros críticos; preferir cancelamento/inativação auditável.

## 16. Regras clínicas
Informações como estabilidade, concentração, compatibilidade, via, apresentação e regras de reutilização devem ter fonte e versão quando utilizadas para decisão operacional.

O software não substitui validação farmacêutica.
