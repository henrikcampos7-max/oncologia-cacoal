"""Configurações seguras por padrão para o MVP local."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "sim", "yes", "on"}


def env_list(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-apenas-desenvolvimento-dados-ficticios"
    else:
        raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY fora do código.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Defina DJANGO_ALLOWED_HOSTS para o ambiente protegido.")

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "oncologia_cacoal.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "oncologia_cacoal.wsgi.application"
ASGI_APPLICATION = "oncologia_cacoal.asgi.application"

USE_SQLITE = env_bool("DJANGO_USE_SQLITE", default=DEBUG and not os.getenv("POSTGRES_DB"))

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "oncologia_cacoal_dev"),
            "USER": os.getenv("POSTGRES_USER", "oncologia_cacoal_dev"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 0,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 15}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Manaus"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "branding"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Os arquivos de usuário são tratados como privados. Não configure um
# servidor web para expor MEDIA_ROOT diretamente; use o endpoint autenticado
# de arquivos de transferência do aplicativo.
MEDIA_URL = "media/"
MEDIA_ROOT = os.getenv("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media"))
SECURE_MEDIA_ENABLED = env_bool("DJANGO_SECURE_MEDIA_ENABLED", default=True)
SECURE_UPLOAD_MAX_BYTES = int(os.getenv("DJANGO_SECURE_UPLOAD_MAX_BYTES", str(25 * 1024 * 1024)))
SECURE_IMAGE_MAX_PIXELS = int(os.getenv("DJANGO_SECURE_IMAGE_MAX_PIXELS", str(25_000_000)))
SECURE_PDF_MAX_PAGES = int(os.getenv("DJANGO_SECURE_PDF_MAX_PAGES", "100"))

TRANSFER_CONFERENCE_CONFIG = {
    "confianca": {"alta": 0.95, "revisao_recomendada": 0.80, "revisao_obrigatoria": 0.0},
    "vision_provider": os.getenv("TRANSFER_VISION_PROVIDER", "mock"),
    "vision_timeout_segundos": int(os.getenv("TRANSFER_VISION_TIMEOUT", "60")),
    "tamanho_maximo_evidencia_mb": 10,
    "imagens_permitidas": ("png", "jpg", "jpeg", "webp"),
    "validade_critica_dias": 30,
    "azure": {
        "endpoint": os.getenv("TRANSFER_AZURE_ENDPOINT", ""),
        "chave": os.getenv("TRANSFER_AZURE_KEY", ""),
        "api_version": os.getenv("TRANSFER_AZURE_API_VERSION", "2024-11-30"),
        "modelo": os.getenv("TRANSFER_AZURE_MODEL", "prebuilt-layout"),
    },
    "google": {
        "token": os.getenv("TRANSFER_GOOGLE_TOKEN", ""),
        "api_endpoint": os.getenv("TRANSFER_GOOGLE_API_ENDPOINT", "https://vision.googleapis.com/v1/images:annotate"),
    },
}

EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("DJANGO_EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_PASSWORD", "")
EMAIL_USE_TLS = env_bool("DJANGO_EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "alertas@oncologia-cacoal.local")

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
