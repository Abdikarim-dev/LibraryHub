from .base import *
from decouple import config


DEBUG = True


ALLOWED_HOSTS = []


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
    }
}


INSTALLED_APPS += [
    "django_extensions",
]


EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)
