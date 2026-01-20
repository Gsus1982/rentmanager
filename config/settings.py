import os
from pathlib import Path
from decouple import config as decouple_config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ===== DJANGO CORE =====
DEBUG = decouple_config('DEBUG', default=False, cast=bool)
SECRET_KEY = decouple_config('SECRET_KEY', default='django-insecure-change-me-in-production')

# En Railway, AUTO_ALLOWED_HOSTS viene del environment
ALLOWED_HOSTS = decouple_config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
if os.environ.get('RAILWAY_ENVIRONMENT'):
    ALLOWED_HOSTS.append('*.up.railway.app')

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
cat > ~/Documents/rentmanager/config/settings.py << 'EOF'
import os
from pathlib import Path
from decouple import config as decouple_config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ===== DJANGO CORE =====
DEBUG = decouple_config('DEBUG', default=False, cast=bool)
SECRET_KEY = decouple_config('SECRET_KEY', default='django-insecure-change-me-in-production')

# En Railway, AUTO_ALLOWED_HOSTS viene del environment
ALLOWED_HOSTS = decouple_config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
if os.environ.get('RAILWAY_ENVIRONMENT'):
    ALLOWED_HOSTS.append('*.up.railway.app')

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

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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

# ===== DATABASE (Railway or Local) =====
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

# ===== AUTHENTICATION =====
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===== INTERNATIONALIZATION =====
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'Europe/Madrid'
USE_I18N = True
USE_TZ = True

# ===== STATIC & MEDIA FILES =====
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ===== DJANGO REST FRAMEWORK =====
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
}

# ===== CORS =====
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

# ===== DEFAULT FIELD =====
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===== APP CONFIGURATION =====
TAX_CONFIG = {
    'LOCAL': {'iva': 21, 'irpf': 19},
    'PISO': {'iva': 21, 'irpf': 19},
}
