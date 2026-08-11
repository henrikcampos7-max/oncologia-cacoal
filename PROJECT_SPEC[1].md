# PROJECT_SPEC.md

## 1. Visão do produto
Aplicação web para gestão operacional do Centro de Oncologia, com acesso por computador e celular, destinada ao controle de pacientes, tratamentos, medicamentos, estoque, movimentações, transferências, sobras, previsão de demanda e compras.

## 2. Unidade principal
- Cacoal: unidade principal de gestão e consolidação do estoque.
- Ji-Paraná: participa principalmente por meio do envio/importação de relatórios de transferência que impactam o estoque consolidado de Cacoal.

## 3. Perfis de acesso
- Administrador do sistema
- Farmacêutico
- Auxiliar de farmácia
- Enfermagem
- Usuário somente leitura

O princípio deve ser menor privilégio: cada perfil acessa somente funções necessárias.

## 4. Módulos principais
1. Autenticação e usuários
2. Perfis e permissões
3. Pacientes
4. Medicamentos e apresentações
5. Protocolos/tratamentos
6. Agenda de aplicações
7. Estoque
8. Movimentações de estoque
9. Importação de relatórios
10. Transferências entre unidades
11. Motor de demanda
12. Controle de sobras
13. Previsão de compras
14. Relatórios e indicadores
15. Auditoria e rastreabilidade
16. Alertas e notificações
17. Integrações externas

## 5. Princípio de cálculo
O sistema deve manter separados:
- consumo individual do paciente;
- demanda consolidada por medicamento;
- estoque disponível;
- sobras válidas;
- necessidade final de compra.

## 6. Prioridade de desenvolvimento
O núcleo operacional deve funcionar antes de integrações e automações avançadas.

Ordem recomendada:
Fundação → usuários → medicamentos → pacientes → protocolos → agenda → estoque → movimentações → demanda → sobras → compras → transferências/importações → relatórios → alertas → integrações.

## 7. Fora do MVP inicial
Até o núcleo estar estável, evitar priorizar:
- integração com WhatsApp;
- notificações avançadas do Windows;
- automações externas complexas;
- dashboards visuais sofisticados;
- IA clínica autônoma.

Esses recursos podem ser adicionados posteriormente sem alterar o motor central.
