# BUSINESS_RULES.md

## Fluxo principal
Demanda bruta → sobras reais disponíveis → estabilidade → possibilidade de reutilização → paciente seguinte/data → alocação de sobra válida → demanda líquida → estoque disponível → apresentações/frascos → nova sobra projetada → possível reaproveitamento futuro → necessidade final de compra.

## Paciente → consumo individual
Calcular protocolo, medicamento, dose, frequência, datas, ocorrências e quantidade prevista.

## Medicamento → demanda consolidada
Somar as demandas individuais de todos os pacientes elegíveis.

## Demanda bruta
Necessidade antes de considerar estoque, sobras, transferências e compras.

## Sobras
Registrar, quando aplicável: medicamento, apresentação, quantidade, unidade, lote, origem, data/hora de abertura, limite de estabilidade, armazenamento, status, paciente de origem, paciente de destino e usuário responsável.

## Sobra real x projetada
Sobra real existe fisicamente e foi registrada. Sobra projetada é somente previsão matemática. Nunca incorporar automaticamente sobra projetada ao estoque físico.

## Reutilização
Somente reduzir demanda quando a sobra estiver válida, estável, armazenada corretamente, não consumida/descartada, tecnicamente reutilizável e rastreável.

## FEFO
Entre sobras equivalentes, priorizar a que perderá estabilidade/validade primeiro.

## Rastreabilidade
Registrar origem paciente A → utilização paciente B, preservando histórico.

## Demanda líquida
Demanda líquida = demanda bruta - sobras válidas alocadas. Nunca permitir valor negativo.

## Estoque
Separar físico, disponível, reservado, bloqueado, quarentena, vencido e transferência em trânsito. Somente estoque autorizado reduz compra.

## Frascos/apresentações
Converter a necessidade líquida para apresentações comerciais e registrar sobra projetada resultante.

## Compra
necessidade operacional - estoque utilizável - transferências confirmadas + estoque de segurança configurado = necessidade de aquisição.

## Transferências Ji-Paraná → Cacoal
Validar duplicidade, medicamento/apresentação, quantidade, origem, data, documento fonte, movimento auditável e confirmação antes de refletir no estoque.

## Auditoria
Registrar usuário, data/hora, ação, valor anterior, valor novo, entidade e origem. Evitar exclusão física de registros críticos.

## Segurança
O software não substitui validação farmacêutica.
