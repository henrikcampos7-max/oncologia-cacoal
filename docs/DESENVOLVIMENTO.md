# Desenvolvimento local

Esta base usa **Django 5.2 LTS** e **PostgreSQL**. Somente dados fictícios são permitidos em desenvolvimento e testes.

## Preparação no Windows

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

O PostgreSQL ainda precisa ser instalado e configurado localmente. Não salve senha no GitHub. Antes de executar a aplicação, defina as variáveis apenas na sessão atual do PowerShell:

```powershell
$env:DJANGO_DEBUG = 'true'
$env:POSTGRES_DB = 'oncologia_cacoal_dev'
$env:POSTGRES_USER = 'oncologia_cacoal_dev'
$env:POSTGRES_PASSWORD = '<defina-localmente>'
python manage.py migrate
python manage.py runserver
```

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
