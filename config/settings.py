import os
from pathlib import Path
from decouple import config as decouple_config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

RAILWAY_ENV = os.environ.get('RAILWAY_ENVIRONMENT')

if RAILWAY_ENV:
    DEBUG = True
else:
    DEBUG = decouple_config('DEBUG', default=True, cast=bool)

SECRET_KEY = decouple_config('SECRET_KEY', default='django-insecure-change-me-in-production')

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'web-production-c26d.up.railway.app']

if os.environ.get('RAILWAY_ENVIRONMENT'):
    ALLOWED_HOSTS.extend([
        'web-production-c26d.up.railway.app',
    ])

CSRF_TRUSTED_ORIGINS = [
    'https://web-production-c26d.up.railway.app',
]

# CSRF & Sessions Configuration
if os.environ.get('RAILWAY_ENVIRONMENT'):
    # Production en Railway (HTTPS detrás de proxy)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_DOMAIN = None
    CSRF_COOKIE_DOMAIN = None
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
else:
    # Desarrollo local
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_DOMAIN = None
    CSRF_COOKIE_DOMAIN = None
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'


USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# NO definimos SESSION_COOKIE_DOMAIN ni CSRF_COOKIE_DOMAIN



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'app',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # DEBE estar aquí
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# SESSION_SAVE_EVERY_REQUEST = True


ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'app' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'Europe/Madrid'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
}

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

TAX_CONFIG = {
    'LOCAL': {'iva': 21, 'irpf': 19},
    'PISO': {'iva': 21, 'irpf': 19},
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'django.contrib.auth': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
