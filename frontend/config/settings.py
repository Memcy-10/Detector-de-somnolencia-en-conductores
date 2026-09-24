"""
settings.py — Configuración de Django
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-somnolencia-sena-2024-dev-key"
)

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1", ".vercel.app"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "drowsiness",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "drowsiness" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

LANGUAGE_CODE = "es-co"
TIME_ZONE     = "America/Bogota"
USE_I18N      = True
USE_TZ        = True

STATIC_URL    = "/static/"
STATIC_ROOT   = BASE_DIR / "staticfiles"

# URL del backend FastAPI
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8001")
