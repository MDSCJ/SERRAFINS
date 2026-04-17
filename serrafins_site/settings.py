from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# ALLOWED_HOSTS: Add your Render domain here, e.g. "serrafins.onrender.com"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost,.onrender.com").split(",") if host.strip()]

# Security settings for production
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

INSTALLED_APPS = [
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # For serving static files in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "core.middleware.CanonicalHostMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "core.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "serrafins_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR, BASE_DIR / "frontend" / "pages"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.auth_profile",
            ],
        },
    },
]

WSGI_APPLICATION = "serrafins_site.wsgi.application"


def _mysql_database_settings(name, user, password, host, port, options=None):
    if options is None:
        options = {}

    try:
        import pymysql
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass

    return {
        "ENGINE": "django.db.backends.mysql",
        "NAME": name,
        "USER": user,
        "PASSWORD": password,
        "HOST": host,
        "PORT": port,
        "CONN_MAX_AGE": 60,
        "OPTIONS": options,
    }

# Supports DATABASE_URL or individual env vars for PostgreSQL/MySQL.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if DATABASE_URL.startswith("mysql://"):
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

    from urllib.parse import urlparse

    parsed = urlparse(DATABASE_URL)
    if parsed.scheme in {"mysql+pymysql", "mysql", "mariadb"}:
        DATABASES = {
            "default": _mysql_database_settings(
                name=parsed.path.lstrip("/"),
                user=parsed.username or os.getenv("MYSQL_USER", "root"),
                password=parsed.password or os.getenv("MYSQL_PASSWORD", ""),
                host=parsed.hostname or os.getenv("MYSQL_HOST", "127.0.0.1"),
                port=parsed.port or os.getenv("MYSQL_PORT", "3306"),
                options={"charset": os.getenv("MYSQL_CHARSET", "utf8mb4")},
            )
        }
    else:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": parsed.path.lstrip("/"),
                "USER": parsed.username,
                "PASSWORD": parsed.password,
                "HOST": parsed.hostname,
                "PORT": parsed.port or 5432,
                "CONN_MAX_AGE": 60,
                "OPTIONS": {"sslmode": os.getenv("AIVEN_SSLMODE", "require")},
            }
        }
else:
    DB_ENGINE = os.getenv("DB_ENGINE", "django.db.backends.sqlite3")
    if DB_ENGINE == "django.db.backends.postgresql":
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.getenv("AIVEN_DB_NAME", "defaultdb"),
                "USER": os.getenv("AIVEN_DB_USER", "avnadmin"),
                "PASSWORD": os.getenv("AIVEN_DB_PASSWORD", ""),
                "HOST": os.getenv("AIVEN_DB_HOST", "localhost"),
                "PORT": os.getenv("AIVEN_DB_PORT", "15432"),
                "CONN_MAX_AGE": 60,
                "OPTIONS": {"sslmode": os.getenv("AIVEN_SSLMODE", "require")},
            }
        }
    elif DB_ENGINE == "django.db.backends.mysql":
        DATABASES = {
            "default": _mysql_database_settings(
                name=os.getenv("MYSQL_DB_NAME", "serrafins"),
                user=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                host=os.getenv("MYSQL_HOST", "127.0.0.1"),
                port=os.getenv("MYSQL_PORT", "3306"),
                options={"charset": os.getenv("MYSQL_CHARSET", "utf8mb4")},
            )
        }
    else:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Session configuration
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400 * 7  # 7 days
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
if DEBUG:
    SESSION_COOKIE_SECURE = False  # Allow HTTP on localhost
else:
    SESSION_COOKIE_SECURE = True  # HTTPS only in production

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "frontend"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"
