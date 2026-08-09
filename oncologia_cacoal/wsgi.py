"""Entrada WSGI do projeto."""

import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oncologia_cacoal.settings")
application = get_wsgi_application()
