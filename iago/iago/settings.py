"""
Django settings for iago project.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
HERE = Path(__file__).parent

# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('API_SECRET', 'debugkey')

LOGGING_LEVEL_MODULE = logging.DEBUG
MAX_DB_THREADS = 16

LOGIN_URL = '/admin/login/'

# silk profiling
SILKY_PYTHON_PROFILER = True
SILKY_PYTHON_PROFILER_BINARY = True
SILKY_AUTHENTICATION = True  # User must login
SILKY_AUTHORISATION = True  # User must have permissions
SILKY_MAX_REQUEST_BODY_SIZE = -1  # Silk takes anything <0 as no limit
SILKY_MAX_RESPONSE_BODY_SIZE = 1024  # If response body>1024 bytes, ignore
SILKY_META = True
SILKY_PYTHON_PROFILER_RESULT_PATH = BASE_DIR/'.tmp/'
os.makedirs(SILKY_PYTHON_PROFILER_RESULT_PATH, exist_ok=True)
# SILKY_INTERCEPT_PERCENT = 50 # log only 50% of requests

if not bool(int(os.getenv('PRODUCTION', '0'))):
    DEBUG = True
    print('DJANGO SETTINGS IN DEBUG')
    # import newrelic.agent
    # newrelic.agent.initialize(HERE.parent/'newrelic.ini')
else:
    DEBUG = False
    print('DJANGO SETTINGS IN PRODUCTION')

ALLOWED_HOSTS = ['*', '127.0.0.1', '[::1]']

CSRF_TRUSTED_ORIGINS = ['https://api.iago.jeeny.ai']

# Application definition

INSTALLED_APPS = [
    'v0',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'rest_framework.authtoken',
    'rest_framework',
    'silk'
    # 'drf_yasg',
]

if DEBUG:
    INSTALLED_APPS.append('django_extensions')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'silk.middleware.SilkyMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# https://docs.djangoproject.com/en/4.0/topics/cache/#database-caching-1
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
    }
}


ROOT_URLCONF = 'iago.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'iago.wsgi.application'

# auth
# https://www.django-rest-framework.org/api-guide/authentication/
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication'
    ]
}

# extensions
GRAPH_MODELS = {
  'all_applications': True,
  'group_models': True,
}

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

# NOTE if the database is ever reset or migrated, ensure that this is done:
# https://stackoverflow.com/questions/14292800/how-to-use-pg-trgm-after-postgresql-installation-from-source/14294609#14294609
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'iago',
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASS'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': '5432',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# logging config
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(name)s] %(asctime)s %(levelname)s %(threadName)s [%(module)s:%(funcName)s:%(lineno)d] | %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'verbose'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO' if not DEBUG else 'INFO', #  NORMALY DEBUG
        },
        # 'daphne': {
        #     'handlers': ['console'],
        #     'level': 'DEBUG'
        # },
    },
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Berlin'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
