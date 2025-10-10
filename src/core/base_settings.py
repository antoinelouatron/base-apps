import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv(".env")

ENV_PREFIX = "DJANGO_"

def get_setting(setting, default=None, cast_type=str):
    """Get setting from environment variable or return exception"""
    env_setting = os.getenv(ENV_PREFIX + setting, default)
    if env_setting is None:
        raise ImproperlyConfigured("Set the {} environment variable".format(ENV_PREFIX + setting))
    try:
        return cast_type(env_setting)
    except ValueError:
        raise ImproperlyConfigured("Cannot cast {} to {}".format(setting, cast_type))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(get_setting(
    "BASE_DIR",
    Path(__file__).resolve().parent.parent
))

SECRET_KEY = get_setting("SECRET_KEY")

DEBUG = get_setting("DEBUG", False, bool)

ALLOWED_HOSTS = []
INTERNAL_IPS = [
    "127.0.0.1",
]
SITE_ID = 1

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "django.forms", # to find form templates
    "webpack_loader",
    "rest_framework",
    "rest_framework.authtoken",
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379",
    },
    "files": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": "/var/tmp/site_cache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# base login config
LOGIN_URL_NAME = "account_login"
LOGIN_URL = "/login"

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []

LOGIN_REDIRECT_URL = "/profil/"
LOGOUT_REDIRECT_URL = "/login/"
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 # 1 day


##################
# REST framework #
##################
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
         "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
          "rest_framework.permissions.IsAdminUser",
     ]
}


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
# STATIC_BASE = BASE_DIR / "static"
# STATICFILES_DIRS = [STATIC_BASE]
# STATICFILE_FINDER = ("django.contrib.staticfiles.finders.FileSystemFinder",
#                      "django.contrib.staticfiles.finders.AppDirectoriesFinder")

STATIC_URL = "static/"
MEDIAFILES_URL = "/media/"
PROTECTED_URL = "/documents/protected/"
ICON_URL = "/media/icon/"

ASSETS_MAP = BASE_DIR / "assets-map.json"

# MEDIA_ROOT = BASE_DIR / "media"
# relative to MEDIA_ROOT
# DOCUMENTS_PATH = "documents"
# PROTECTED_PATH = "protected"

# static chapters and json files
# STATIC_HTML_ROOT = STATIC_BASE / "www"
# STATIC_HTML_URL = "/static/www/"
# FILE_UPLOAD_PERMISSIONS = 0o644
# BACKUP_PATH = MEDIA_ROOT / "protected" / "archives" # store backup files in protected folder

# COLLES_PDF_PATH = MEDIA_ROOT / "protected" / "colles"

#sendfile
# SENDFILE_BACKEND = 'django_sendfile.backends.nginx'
# SENDFILE_ROOT = MEDIA_ROOT / "protected"
# SENDFILE_URL = "/media/protected"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

#######################
# Email configuration #
#######################

# SERVER_EMAIL = "noreply@louatron.fr"
# DEFAULT_FROM_EMAIL = "noreply@louatron.fr"
# ADMINS = [
#     ('antoine', 'antoine.louatron@gmail.com'),
# ]
# MANAGERS = ADMINS



#########################
# App specific settings #
#########################

AGENDA_OFFICIAL_ICAL_URL = "https://fr.ftp.opendatasoft.com/openscol/fr-en-calendrier-scolaire/Zone-B.ics"
AGENDA_ICAL_FILE = BASE_DIR / "agenda" / "gouv.ical.ics"


QUILL_CONFIGS = {
    "default": {
        "theme": "snow",
        "modules": {
            "syntax": True,
            "toolbar": [
                [
                    "bold",
                    "italic",
                    "underline",
                    "blockquote",
                ],
                ["code-block", "link", "formula"],
            ],
            "history": {
                "delay": 1000,
                "maxStack": 50,
                "userOnly": True
            }
        },
        #'formats': ["", "formula"],
    },
    "colle_comment": {
        "theme": "snow",
        "modules": {
            "toolbar": [
                [
                    "bold",
                    "italic",
                    "underline",
                    "blockquote",
                ],
            ],
            "history": {
                "delay": 1000,
                "maxStack": 50,
                "userOnly": True
            }
        }
    }
}

##############################
# Archive and backup settings #
##############################

# DB_BACKUP_COMMANDS = {
#     "django.db.backends.postgresql" : {
#         "command": "/usr/local/pgsql/bin/pg_dump",
#         "base": "-F c", # optional
#         "USER": "-U {USER}",
#         "HOST": "-h {HOST}",
#         "PORT": "-p {PORT}",
#         "NAME": "-d {NAME}",
#         "output": "-f {FILE}",
#     }
# }

# Logging
# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "formatters": {
#         "default": {
#             "format": "[%(asctime)s] %(levelname)s: %(message)s",
#         }
#     },
#     "handlers": {
#         "file": {
#             "class": "logging.handlers.TimedRotatingFileHandler",
#             "filename": "/var/log/siteprepa/siteprepa.log",
#             "when": "midnight",
#             "backupCount": 60,
#             "formatter": "default",
#         },
#     },
#     "root": {
#         "handlers": ["file"],
#         "level": "INFO",
#     },
# }
