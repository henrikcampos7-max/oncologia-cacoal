# Especificação visual e funcional baseada nas referências do OncoManager

## Objetivo

Recriar no projeto **Oncologia Cacoal** a organização visual e os fluxos observados nas capturas fornecidas pelo usuário, sem acessar o código restrito, sem contornar permissões e sem copiar a marca OncoManager. A interface deve usar a identidade oficial da Unimed Centro Rondônia e incorporar também o escopo administrativo já aprovado para previsão de demanda, estoque, compras, auditoria e relatórios.

As capturas originais permanecem somente na pasta local de referências fora deste repositório, pois uma delas exibe um e-mail. Nenhuma credencial ou imagem com dado pessoal deve ser enviada ao GitHub ou usada como dado de demonstração.

## Identidade e leiaute

- Nome na interface: **Oncologia Cacoal**.
- Cabeçalho e navegação com a marca oficial fornecida em `branding/logo_unimed_extraida.png`.
- Verde principal `#00824A`, verde complementar `#009B63`, texto `#373435`, bordas `#CFCFCF` e fundo `#FFFFFF`.
- Barra lateral fixa no computador e recolhível no celular.
- Cartões brancos, bordas suaves, campos amplos e tabelas com rolagem horizontal no celular.
- Item ativo da navegação destacado em verde institucional.
- Não deformar, redesenhar ou recriar a marca com IA.
- Não copiar o nome, logotipo ou paleta azul-petróleo do OncoManager.

## Tela de acesso

- Leiaute dividido no computador: painel institucional à esquerda e formulário à direita.
- Painel institucional com marca Unimed/Oncologia Cacoal, título sobre gestão segura de tratamentos e texto resumindo agenda, pacientes, medicamentos, estoque e previsão de demanda.
- Formulário com e-mail, senha, botão **Entrar**, link **Criar conta** e recuperação de senha.
- No celular, empilhar o painel e o formulário, priorizando o formulário.
- Nunca preencher credenciais automaticamente nem exibir e-mail real em captura ou demonstração.
- Manter autenticação, isolamento por clínica e perfis de acesso.

## Navegação principal

O menu inicial deve conter:

1. Painel.
2. Agenda.
3. Pacientes e Tratamentos.
4. Medicamentos e Apresentações.
5. Quantitativo e Previsão.
6. Estoque, Lotes e Validades.
7. Transferências.
8. Pedidos, Compras e Recebimentos.
9. Importações.
10. Alertas.
11. Relatórios e Indicadores.
12. Usuários, Permissões e Auditoria.

O rodapé da barra lateral deve mostrar o usuário autenticado e a opção **Sair**.

## Agenda de tratamentos

- Filtro por data.
- Busca por nome do paciente.
- Filtro por protocolo/tratamento.
- Exportação da listagem em CSV e PDF.
- Tabela com hora, paciente, protocolo, medicamentos e status.
- Estado vazio informando que não há tratamentos na data.
- Bloco **Próximo dia de tratamento** com paciente, protocolo vinculado, ciclo, dia do ciclo, data e ação de registro.
- Impedir duplicidade silenciosa de aplicação e sinalizar divergências de data, dose, ciclo ou origem.

## Pacientes e tratamentos

- Cadastro com nome, diagnóstico, protocolo terapêutico e data de início.
- Campos de apoio para peso, altura, superfície corporal, sexo e TFG.
- Superfície corporal calculada como apoio e claramente identificada como resultado que exige validação humana.
- Inclusão repetível de medicamentos do protocolo.
- Para cada item: medicamento, ciclos, dias do ciclo, valor da posologia, unidade e dose calculada.
- Unidades previstas: dose fixa, mg, mg/kg e mg/m², sem conversão implícita.
- Botão para adicionar medicamento e ação para salvar o paciente.
- Listagem com nome, diagnóstico, protocolo, início e medicamentos.
- Nenhuma dose, protocolo ou equivalência deve ser definida ou alterada automaticamente.

## Medicamentos e apresentações

- Cadastro de nome do medicamento, concentração, apresentação e quantidade por frasco.
- Separar medicamento de suas apresentações para permitir mais de um frasco/apresentação por produto.
- Listagem de cadastrados com nome, concentração, apresentação e quantidade por frasco.
- Exclusão preferencialmente lógica e sempre com confirmação, permissão e auditoria.
- Ampliar posteriormente com unidade clínica, unidade de estoque, unidade comercial, fator de conversão, custo, fornecedor e prazo de entrega.

## Quantitativo e previsão de frascos

- Seleção de data inicial e final.
- Ação **Calcular** e total de frascos em destaque.
- Tabela com medicamento, apresentação, administrações, dose total, quantidade por frasco e frascos necessários.
- Usar os tratamentos agendados no período como fonte do cálculo.
- Arredondamento para cima somente após validar unidade, apresentação e fator de conversão.
- Mostrar metodologia, dados usados, divergências e necessidade de validação farmacêutica.
- Não assumir compartilhamento de sobras, estabilidade, equivalência ou fracionamento sem regra aprovada.

## Funcionalidades adicionais já solicitadas

- Importação de previsão e de estoque por Excel/CSV com detecção de cabeçalhos, mapeamento, prévia e classificação de erros.
- Estoque atual, posições, movimentações, reservas, ajustes e conciliação.
- Lotes, validades, bloqueios e rastreabilidade.
- Transferências entre unidades.
- Lista de compras, pedidos, recebimentos e acompanhamento de pendências.
- Alertas de falta, estoque mínimo, validade, divergência, importação pendente e tratamento sem cobertura.
- Painel com aplicações próximas, itens críticos, compras pendentes, transferências em trânsito e importações aguardando validação.
- Relatórios e indicadores com exportação controlada.
- Auditoria de cadastro, alteração, importação, aprovação, ajuste e exclusão lógica.
- Perfis: administrador, farmacêutico, auxiliar, enfermagem, gestor e somente leitura.

## Critérios de segurança e aceite

- Usar somente dados fictícios em desenvolvimento, testes e demonstrações.
- Isolar dados por clínica e usuário; testar acesso indevido.
- Toda operação crítica deve indicar responsável, data, motivo e origem.
- Exigir revisão humana antes de alterar dose, estoque, compra, cadastro ou exclusão.
- Não publicar nem usar dados reais sem aprovação formal de segurança, LGPD e responsáveis clínicos.
- Entregar cada módulo com critérios de aceite, testes e indicação clara do que ainda é protótipo.

