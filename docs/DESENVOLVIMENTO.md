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
