"""Entrada ASGI do projeto."""

import os

from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oncologia_cacoal.settings")
application = get_asgi_application()
