# PROJECT_SPEC.md

## Visão
Aplicação web para gestão do Centro de Oncologia, acessível por computador e celular, destinada ao controle de pacientes, tratamentos, medicamentos, estoque, movimentações, transferências, sobras, previsão de demanda e compras.

## Unidades
- Cacoal: unidade principal e estoque consolidado.
- Ji-Paraná: envia/importa transferências que devem impactar o estoque de Cacoal conforme regras de confirmação.

## Perfis
- Administrador
- Farmacêutico
- Auxiliar de farmácia
- Enfermagem
- Somente leitura

Aplicar princípio do menor privilégio.

## Módulos
Autenticação; usuários/permissões; pacientes; medicamentos/apresentações; protocolos; tratamentos; agenda; estoque; movimentações; transferências; importação; demanda; sobras; compras; relatórios; auditoria; alertas; integrações.

## Separação obrigatória
- consumo individual do paciente;
- demanda consolidada do medicamento;
- estoque;
- sobra real;
- sobra projetada;
- necessidade final de compra.

## Ordem recomendada
Fundação → usuários → medicamentos → pacientes → protocolos → agenda → estoque → movimentações → demanda → sobras → compras → transferências/importações → relatórios → alertas → integrações.

## Não priorizar no MVP
WhatsApp, notificações avançadas, dashboards sofisticados, integrações complexas e IA clínica autônoma.
