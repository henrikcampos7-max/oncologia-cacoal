# ARCHITECTURE.md

## Objetivo
Manter arquitetura simples, modular e segura. Não reinventar a arquitetura durante cada feature.

## Camadas sugeridas
1. UI
2. Regras de aplicação/use cases
3. Domínio/regras de negócio
4. Acesso a dados
5. Integrações externas
6. Auditoria/logs

## Domínios
- auth
- users
- patients
- medications
- protocols
- scheduling
- inventory
- inventory-movements
- transfers
- demand
- leftovers
- purchasing
- reports
- audit
- integrations

## Princípios
- Separar regras de negócio da interface.
- Não fazer cálculos críticos diretamente em componentes visuais.
- Não duplicar fórmulas em frontend e backend.
- Centralizar o motor de demanda.
- Centralizar o motor de sobras.
- Manter funções críticas testáveis.
- Utilizar transações para operações de estoque quando necessário.
- Registrar auditoria para ações críticas.
- Dados clínicos/operacionais sensíveis devem respeitar requisitos de segurança e privacidade.

## APIs/serviços
Cada módulo deve expor operações pequenas e específicas.

Exemplo:
- calculatePatientDemand()
- consolidateMedicationDemand()
- getValidLeftovers()
- allocateLeftovers()
- calculateNetDemand()
- calculatePresentationRequirements()
- calculatePurchaseNeed()

Evitar uma única função que faça todo o fluxo sem etapas observáveis.

## Banco
O schema definitivo deve acompanhar a stack real do repositório.

Entidades conceituais esperadas:
- User
- Role
- Patient
- Medication
- MedicationPresentation
- Protocol
- ProtocolMedication
- Treatment
- TreatmentSchedule
- InventoryItem
- InventoryMovement
- Transfer
- Leftover
- LeftoverAllocation
- DemandForecast
- PurchaseForecast
- AuditLog
- ImportedDocument

## Regra de arquitetura
Antes de criar nova camada, framework, dependência ou padrão, verificar se o projeto já possui solução equivalente.
