"""
Django settings for cobijo_vzla project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# ==========================================
# SEGURIDAD (leído desde .env)
# ==========================================
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("❌ DJANGO_SECRET_KEY no está definida en el .env")

DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.getenv(
    'DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1'
).split(',')

CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS if host != 'localhost']


# ==========================================
# APLICACIONES
# ==========================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'rest_framework',
    'leaflet',
    'apps.core',
    'apps.emergencias',
    'apps.optimizacion',
    'apps.mapa',
    'apps.reportes',
    'apps.publico',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cobijo_vzla.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'cobijo_vzla.wsgi.application'


# ==========================================
# BASE DE DATOS
# ==========================================
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    # --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
    # Forzamos el uso del backend de PostGIS, ya que la URL
    # empieza con 'postgresql://' y dj_database_url no lo detecta.
    DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'
    
    # search_path necesario para que PostGIS encuentre el esquema 'gis'
    DATABASES['default']['OPTIONS'] = {
        'options': '-c search_path=public,gis'
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': os.getenv('DB_NAME', 'cobijo_vzla_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }


# ==========================================
# VALIDACIÓN DE CONTRASEÑAS
# ==========================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ==========================================
# INTERNACIONALIZACIÓN
# ==========================================
LANGUAGE_CODE = 'es-ve'
TIME_ZONE = 'America/Caracas'
USE_I18N = True
USE_TZ = True


# ==========================================
# ARCHIVOS ESTÁTICOS Y MEDIA
# ==========================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ==========================================
# LEAFLET
# ==========================================
LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (10.0, -66.0),
    'DEFAULT_ZOOM': 7,
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
}


# ==========================================
# DJANGO REST FRAMEWORK
# ==========================================
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ]
}


# ==========================================
# AUTENTICACIÓN
# ==========================================
LOGIN_REDIRECT_URL = '/panel/'
LOGOUT_REDIRECT_URL = '/'


# ==========================================
# EMAIL
# ==========================================
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)

# ==========================================
# GEODJANGO - Rutas a librerías nativas
# ==========================================
# En Windows, GDAL y GEOS se instalan vía OSGeo4W y hay que apuntar
# a las DLLs. En Linux/Mac se instalan por el sistema y no hace falta.
if os.name == 'nt':
    GDAL_LIBRARY_PATH = os.getenv('GDAL_LIBRARY_PATH')
    GEOS_LIBRARY_PATH = os.getenv('GEOS_LIBRARY_PATH')

    # ==========================================
# CACHÉ
# ==========================================
# Cache basado en archivos: comparte datos entre procesos
# (útil con gunicorn multi-worker y entre comandos manage.py)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / '.cache',
        'TIMEOUT': 1800,  # 30 minutos por defecto
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        },
    }
}

# Crear el directorio si no existe
os.makedirs(BASE_DIR / '.cache', exist_ok=True)