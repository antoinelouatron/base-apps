from pathlib import Path
from core.base_settings import *  # noqa

ROOT_URLCONF = "urls"
DEFAULT_PROTOCOL = "http"
ALLOWED_HOSTS = ["*"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": get_setting("DB_NAME"),
        "USER": get_setting("DB_USER"),
        "PASSWORD": get_setting("DB_PASSWORD"),
        "HOST": get_setting("DB_HOST"),
        "TEST": {
            "NAME": get_setting("TEST_DB_NAME"),
        }
    },
}

INSTALLED_APPS += [
    "dev",
    "core",
    "users",
    "agenda",
    "bulkimport",
    "utils",
    "quill_editor",
    "base_archives"
]

LOGIN_REDIRECT_URL = "/profil/"
LOGOUT_REDIRECT_URL = "/login/"

DEBUG = False

TEST_RUNNER = "dev.test_utils.DjangoRunner"

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "users.middlewares.SeeAsMiddleware",
]


FORM_RENDERER = "utils.forms.renderer.CustomRenderer"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "users.emailbackend.EMailBackend",
]

DJANGO_VITE = {
  "default": {
    "dev_mode": False,
    "manifest_path": BASE_DIR / ".." / "tests" /"manifest.json",
    "static_url_prefix": "js/"  # must match the `base` option in vite.config.js
  }
}
VITE_ALIAS_MAP = ""


AGENDA_ICAL_FILE = BASE_DIR / "agenda" / "gouv.ical.ics"
# directory where db backups are stored
BACKUP_PATH = Path(__file__).parent / "backups"
SENDFILE_ROOT = BACKUP_PATH.parent
SENDFILE_BACKEND = "django_sendfile.backends.development"

MISSING_ASSET_LOG_LEVEL = "warning"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s: %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "ERROR",
    },
}
