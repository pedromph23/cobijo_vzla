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
# SEGURIDAD ADICIONAL (producción)
# ==========================================
# Las protecciones se activan cuando DEBUG=False. En desarrollo se
# desactivan para no romper el flujo local (HTTP sin SSL).
#
# Notas:
# - Render actúa como proxy SSL. Sin SECURE_PROXY_SSL_HEADER, Django no
#   sabe que la petición original fue HTTPS y rompe CSRF/redirects.
# - HSTS por defecto: 1 año en producción, 0 en desarrollo.
# - Las cookies solo se envían por HTTPS en producción.

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = os.getenv(
    'DJANGO_SECURE_SSL_REDIRECT',
    'False' if DEBUG else 'True'
).lower() == 'true'

SECURE_HSTS_SECONDS = int(os.getenv(
    'DJANGO_SECURE_HSTS_SECONDS',
    '0' if DEBUG else '31536000'
))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG


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
    'apps.core.middleware.AuditoriaMiddleware',
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
    DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'
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
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        # Global para anónimos: 60 requests/minuto (1 req/seg promedio).
        'anon': '60/min',
        # Endpoints sensibles con rates específicos (ver apps/core/throttles.py).
        'reporte_ciudadano': '5/hour',
        'mapa_calor_publico': '30/min',
        'buscar_lugar': '30/min',
    },
}


# ==========================================
# AUTENTICACIÓN
# ==========================================
LOGIN_REDIRECT_URL = '/panel/'
LOGOUT_REDIRECT_URL = '/'


# ==========================================
# SESIONES Y COOKIES
# ==========================================
# Cookies de sesión endurecidas:
# - HTTPOnly: JS no puede leer la cookie (previene XSS).
# - SameSite=Lax: previene CSRF cross-site pero permite navegación normal.
# - Timeout de 8 horas (jornada laboral típica).
# - La sesión expira al cerrar el navegador solo si SESSION_EXPIRE_AT_BROWSER_CLOSE=True.
#
# CSRF_COOKIE_HTTPONLY se deja False porque Django necesita leer el token
# desde el DOM para el JavaScript que envía formularios AJAX.

SESSION_COOKIE_AGE = 8 * 60 * 60  # 8 horas
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_AGE = 8 * 60 * 60


# ==========================================
# EMAIL
# ==========================================
# Desarrollo: consola por defecto.
# Producción: configurar un backend SMTP mediante variables de entorno.
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    'Cobijo VZLA <no-reply@localhost>'
)
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '10'))

# No bloquear el arranque de Django por la configuración SMTP.
# La conexión y validación efectiva del proveedor ocurren cuando
# una funcionalidad de correo intenta enviar un mensaje.
# En producción, EMAIL_USE_TLS y EMAIL_USE_SSL deben configurarse
# de acuerdo con el proveedor SMTP utilizado.


# ==========================================
# GEODJANGO - Rutas a librerías nativas
# ==========================================
if os.name == 'nt':
    GDAL_LIBRARY_PATH = os.getenv('GDAL_LIBRARY_PATH')
    GEOS_LIBRARY_PATH = os.getenv('GEOS_LIBRARY_PATH')


# ==========================================
# LOGGING
# ==========================================
# Configuración de logging para producción y desarrollo.
#
# - En producción (Render): todo va a stdout, capturado por Render Logs.
# - En desarrollo: además va a consola con formato más legible.
#
# Niveles:
#   - INFO en apps propias (core, mapa, optimizacion, publico, reportes).
#   - WARNING en Django y dependencias para reducir ruido.
#   - ERROR se registra siempre con traceback.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Apps propias: INFO para diagn'ostico
        'apps.core': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.mapa': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.optimizacion': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.publico': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.reportes': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.emergencias': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


# ==========================================
# CACHÉ
# ==========================================
# DatabaseCache: usa la misma conexión a Supabase que el resto de la app.
# Ventajas sobre FileBasedCache:
# - Compartido entre los 2 workers de gunicorn (un solo estado).
# - Los throttles funcionan correctamente (rate real, no rate × workers).
# - Invalidaciones de caché consistentes.
# - Sin servicios externos adicionales (Redis, Memcached).
#
# Requiere: `python manage.py createcachetable` (una sola vez).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cobijo_cache',
        'TIMEOUT': 1800,
        'OPTIONS': {
            'MAX_ENTRIES': 5000,
            'CULL_FREQUENCY': 3,
        },
    }
}
