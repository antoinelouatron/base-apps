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

# users/agenda ont été rapatriés dans le consommateur (blaise-colles). base_sites
# ne teste plus que ses modules génériques, avec le User Django par défaut.
INSTALLED_APPS += [
    "dev",
    "core",
    "bulkimport",
    "utils",
    "quill_editor",
    "base_archives"
]

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

DEBUG = False

TEST_RUNNER = "dev.test_utils.DjangoRunner"

# Permission générique (superuser, sans rôle) injectée dans base_archives.DownloadDb.
ARCHIVES_DOWNLOAD_PERMISSION = "utils.permissions.SUPERUSER"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


FORM_RENDERER = "utils.forms.renderer.CustomRenderer"

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
