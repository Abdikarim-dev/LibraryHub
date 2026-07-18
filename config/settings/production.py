from .base import *
from decouple import config


DEBUG = False


ALLOWED_HOSTS = [
    "library.com",
    "www.library.com",
]


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


SECURE_SSL_REDIRECT = True


SESSION_COOKIE_SECURE = True


CSRF_COOKIE_SECURE = True


SECURE_HSTS_SECONDS = 31536000


SECURE_BROWSER_XSS_FILTER = True