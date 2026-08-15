# Tratamento seguro de arquivos

Este projeto recebe arquivos sensíveis em dois fluxos principais: relatórios de transferência e evidências fotográficas. O módulo `core.file_security` centraliza os controles de filesystem que devem ser usados antes de persistir qualquer arquivo controlado por usuário.

## Objetivos

- impedir path traversal (`../`, caminhos absolutos e escapes de raiz);
- impedir symlinks que redirecionem uma gravação para fora da raiz autorizada;
- nunca usar o nome enviado pelo cliente como identidade do arquivo persistido;
- aplicar limites de tamanho e extensões permitidas;
- calcular SHA-256 em streaming para deduplicação e rastreabilidade;
- manter autorização de negócio separada da segurança do filesystem.

## API principal

### `safe_resolve(root, relative_path)`

Resolve somente caminhos relativos e verifica que o destino permanece dentro de `root`.

### `safe_real_destination(root, relative_path)`

Além da contenção de caminho, verifica componentes existentes e ancestrais reais para bloquear symlink escape.

### `sanitize_filename(filename)`

Remove diretórios fornecidos pelo cliente e normaliza caracteres perigosos. O nome sanitizado não deve ser usado como identificador único.

### `build_upload_name(prefix, filename, extension_allowlist=...)`

Gera um nome aleatório com extensão controlada. Exemplo:

```python
from core.file_security import build_upload_name

nome = build_upload_name(
    "transferencias/evidencias",
    arquivo.name,
    extension_allowlist={".jpg", ".jpeg", ".png"},
)
```

O resultado se parece com:

```text
transferencias/evidencias/8f2d...c91a.jpg
```

### `validate_uploaded_file(uploaded, ...)`

Valida tamanho e extensão antes da persistência. MIME type sozinho não é considerado mecanismo suficiente para validar o conteúdo.

### `sha256_stream(stream)` / `sha256_file(path)`

Calcula SHA-256 sem carregar arquivos grandes inteiros na memória.

## Política recomendada para os uploads do projeto

### Evidências fotográficas

Para `TransferenciaEvidencia.arquivo`:

- aceitar somente `.jpg`, `.jpeg`, `.png` conforme a política da aplicação;
- limitar tamanho do upload;
- gerar nome aleatório;
- preservar o original, sem sobrescrever uma evidência existente;
- calcular SHA-256;
- marcar duplicidade pelo hash, sem excluir automaticamente;
- manter revisão humana antes de qualquer integração ao estoque.

### Relatórios PDF

Para `Transferencia.relatorio_arquivo`:

- aceitar somente PDF;
- limitar tamanho;
- gerar nome aleatório;
- calcular SHA-256 antes do processamento;
- deduplicar pelo hash;
- extrair conteúdo em processo separado da aprovação de estoque;
- nunca usar o nome original para construir um caminho local.

## ZIP/TAR e outros pacotes

Se o projeto futuramente receber arquivos compactados, a contenção deve ocorrer **durante a extração**, e não somente depois. Cada entrada deve ser validada com `safe_resolve` antes de ser criada.

Também devem ser rejeitadas entradas que sejam symlinks/hardlinks quando a política do pacote não os autorizar.

## Modelo de ameaça

O arquivo enviado pelo usuário é considerado **não confiável**. O nome, extensão, tamanho, conteúdo e metadados podem ser manipulados.

A regra de segurança é:

```text
usuário/agente
    ↓
arquivo não confiável
    ↓
validação de entrada
    ↓
autorização de negócio
    ↓
path containment + symlink check
    ↓
nome interno aleatório
    ↓
SHA-256
    ↓
persistência
    ↓
processamento isolado
    ↓
revisão/aprovação humana quando aplicável
```

## Importante

Segurança de filesystem não substitui autenticação, autorização por clínica, validação do formato real do arquivo, proteção contra malware, limites de processamento ou isolamento do OCR. Esses controles devem permanecer em camadas independentes.
