# ARCHITECTURE.md

## Princípios
- Regras de negócio separadas da interface.
- Não duplicar fórmulas.
- Motor de demanda centralizado.
- Motor de sobras centralizado.
- Funções críticas testáveis.
- Auditoria em operações sensíveis.
- Transações para movimentações de estoque quando necessárias.

## Domínios
`auth`, `users`, `patients`, `medications`, `protocols`, `scheduling`, `inventory`, `inventory-movements`, `transfers`, `demand`, `leftovers`, `purchasing`, `reports`, `audit`, `integrations`.

## Funções conceituais
`calculatePatientDemand()`, `consolidateMedicationDemand()`, `getValidLeftovers()`, `allocateLeftovers()`, `calculateNetDemand()`, `calculatePresentationRequirements()`, `calculatePurchaseNeed()`.

Evitar uma função única gigantesca para todo o fluxo.

## Entidades conceituais
User, Role, Patient, Medication, MedicationPresentation, Protocol, ProtocolMedication, Treatment, TreatmentSchedule, InventoryItem, InventoryMovement, Transfer, Leftover, LeftoverAllocation, DemandForecast, PurchaseForecast, AuditLog, ImportedDocument.

Antes de criar nova dependência, camada ou padrão, verificar se o projeto já possui solução equivalente.
