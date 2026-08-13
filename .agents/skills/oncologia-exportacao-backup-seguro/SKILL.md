---
name: oncologia-exportacao-backup-seguro
description: Implementar e revisar exportações, relatórios e backups da Oncologia Cacoal. Usar em CSV, Excel, PDF, cópias, restauração, trilha de auditoria e prevenção de vazamentos.
---

# Exportação e backup seguro

Aplicar as regras permanentes do repositório e o Modo de Economia de Tokens.

## Fluxo

- Exportar apenas o período, módulo e campos solicitados.
- Aplicar autorização e registrar usuário, data, filtros e tipo de arquivo na auditoria.
- Não incluir senha, token, cookie, chave, dado clínico desnecessário ou identificador real em demonstrações.
- Gerar arquivo novo sem sobrescrever a origem e validar tamanho, conteúdo e formato.
- Em backup, documentar destino, retenção, integridade e restauração; não alegar sucesso sem verificação.
- Usar dados sintéticos em testes de download e impressão.

## Saída

Informar somente alteração, arquivos, testes executados e pendências ou riscos reais.
