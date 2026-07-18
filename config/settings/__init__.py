import os

if os.getenv("DJANGO_SETTINGS_ENV", "development").lower() == "production":
    from .production import *
else:
    from .development import *
