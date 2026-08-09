# Desenvolvimento local

Esta base usa **Django 5.2 LTS** e **PostgreSQL**. Somente dados fictícios são permitidos em desenvolvimento e testes.

## Preparação no Windows

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Para instalar o PostgreSQL 17, criar o banco e usuário exclusivos, aplicar as migrações e carregar dados inteiramente fictícios, execute:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configurar_postgresql_local.ps1
```

O script instala uma distribuição portátil do PostgreSQL somente para o usuário atual, sem serviço externo e sem exigir permissão de administrador. As senhas aleatórias ficam criptografadas pelo Windows em `%LOCALAPPDATA%\OncologiaCacoal`; nenhum segredo é salvo no repositório.

Depois da configuração, inicie o ambiente local com:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\iniciar_desenvolvimento.ps1
```

O configurador também cria o atalho **Oncologia Cacoal** na Área de Trabalho. Ele executa `scripts\abrir_oncologia_cacoal.ps1`, inicia banco e aplicação quando necessário e abre `http://127.0.0.1:8000/` no navegador padrão.

Para reaplicar a carga fictícia e idempotente ao iniciar, acrescente `-DadosFicticios`. O comando demonstrativo é bloqueado quando `DEBUG` está desativado e usa dose zero, sem orientação clínica ou operacional.

A verificação sem acesso ao banco fica em `http://127.0.0.1:8000/saude/`.

## Testes iniciais

```powershell
$env:DJANGO_DEBUG = 'true'
python manage.py check
python manage.py test core
```

O servidor de desenvolvimento não deve ser usado na rede interna nem com dados reais. HTTPS, banco protegido, backups, revisão de segurança e LGPD são pré-requisitos para produção.

## Interface implementada nesta branch

Após configurar o PostgreSQL e executar `python manage.py migrate`, a primeira entrega local inclui:

- `/entrar/`: acesso por usuário ou e-mail e senha;
- `/`: painel administrativo;
- `/agenda/`: filtros, registro de sessão, CSV e impressão/PDF;
- `/pacientes/`: cadastro e listagem com superfície corporal informativa;
- `/medicamentos/`: medicamento e apresentações;
- `/quantitativo/`: previsão por período e inconsistências de cálculo;
- páginas de escopo para estoque, transferências, compras, importações, alertas, relatórios e auditoria.

Crie a clínica, o usuário e o `PerfilUsuario` inicialmente pelo `/admin/`. O cadastro público permanece desabilitado até a definição do fluxo de aprovação e recuperação de acesso.

Os cálculos são apoio administrativo e não substituem validação farmacêutica. Não use dados reais no ambiente local.
