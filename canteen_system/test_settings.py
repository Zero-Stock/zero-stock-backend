# canteen_system/test_settings.py
# Override database to SQLite for local testing without PostgreSQL
from .settings import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
