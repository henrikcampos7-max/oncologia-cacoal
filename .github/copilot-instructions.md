# Instruções permanentes do repositório

Este repositório contém um sistema web de gestão farmacêutica oncológica para previsão de demanda, estoque, sobras, transferências e compras.

## Contexto operacional

- Unidade principal: Centro de Oncologia de Cacoal.
- Ji-Paraná pode anexar relatório de transferência que será validado e integrado ao estoque de Cacoal.
- Perfis previstos: administrador, farmacêutico, auxiliar de farmácia, enfermagem e somente leitura.
- O sistema deve separar rigorosamente paciente, ocorrência/agendamento, medicamento, apresentação, lote, estoque, sobra e compra.

## Regras de engenharia

- Antes de editar, inspecione arquitetura, linguagem, dependências, testes, convenções e mudanças locais.
- Preserve a tecnologia e o padrão já existentes; não substitua a arquitetura sem justificativa e aprovação.
- Faça alterações pequenas, rastreáveis e compatíveis com o restante do projeto.
- Nunca invente nomes de tabelas, rotas ou campos: confirme-os no código e nas migrações.
- Centralize cálculos de domínio em serviços puros, determinísticos, tipados e testáveis; não os espalhe por telas.
- Use transações para movimentações de estoque e proteja contra duplicidade, concorrência e saldo negativo.
- Valores monetários e quantidades não podem usar arredondamento binário impreciso.
- Datas devem ter fuso e semântica definidos. Diferencie data clínica, competência mensal, validade e data/hora de movimentação.
- Toda mudança de saldo deve gerar histórico imutável com origem, motivo, usuário, data/hora e correlação.
- Não registre dados pessoais ou clínicos em logs, mensagens de erro, fixtures públicas ou screenshots.
- Nunca inclua segredos, tokens, senhas ou credenciais no repositório.
- Execute lint, checagem de tipos, testes e build disponíveis antes de concluir.
- Relate arquivos alterados, testes executados, limitações e riscos residuais.

## Hierarquia obrigatória dos cálculos

1. Paciente e ocorrência: consumo individual por data e competência.
2. Medicamento: consolidação das ocorrências por princípio ativo/apresentação compatível.
3. Operação: demanda bruta, sobras válidas, demanda líquida, estoque disponível e compra.

Nunca desconte estoque ou sobras duas vezes. Nunca arredonde frascos no nível do paciente quando a regra aprovada permitir consolidação por sessão ou período.

## Previsão baseada em agenda e ciclos

- Diferencie ocorrência confirmada, prevista pelo esquema, provável, cancelada, adiada, realizada e não realizada.
- Uma projeção de ciclo não deve virar agendamento confirmado sem ação humana ou integração autorizada.
- Cada ocorrência prevista deve manter vínculo com paciente, plano terapêutico, ciclo, dia do ciclo, data-base, regra que originou a data e versão do plano.
- Mudanças na data de início devem recalcular apenas eventos futuros elegíveis, preservando histórico e alterações manuais.
- Mostre separadamente demanda confirmada, demanda projetada e demanda potencial; não some os cenários como se fossem consumo único.
- A previsão deve ser explicável da consolidação mensal até a ocorrência individual que a originou.
- Nunca projete dose ausente, protocolo incompleto ou quantidade de ciclos indefinida como certeza. Sinalize a lacuna.

## Segurança clínica

- O sistema é apoio operacional e não substitui validação do farmacêutico ou prescrição médica.
- Regras clínicas e farmacêuticas precisam registrar fonte, versão, vigência e responsável pela aprovação.
- Se uma regra estiver ambígua, pare e solicite decisão; não faça inferência silenciosa.
- Alterações de dose, protocolo, estabilidade, compatibilidade ou reutilização exigem revisão humana explícita.
- Use dados sintéticos e anonimizados em testes.
