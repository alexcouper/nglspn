"""WSGI config for project_showcase project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_showcase.settings")

# Initialize OpenTelemetry (also called from gunicorn post_fork for worker processes)
from project_showcase.otel import init_otel

init_otel()

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
