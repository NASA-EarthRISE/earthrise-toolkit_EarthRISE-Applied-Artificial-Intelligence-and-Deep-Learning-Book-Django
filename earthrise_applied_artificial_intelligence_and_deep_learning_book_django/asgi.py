"""
ASGI config for earthrise_applied_artificial_intelligence_and_deep_learning_book_django project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "earthrise_applied_artificial_intelligence_and_deep_learning_book_django.settings",
)

application = get_asgi_application()
