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

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
HERE = Path(__file__).parent

# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('API_SECRET', 'debugkey')

if not bool(int(os.getenv('PRODUCTION', '0'))):
    DEBUG = True
    print('DJANGO SETTINGS IN DEBUG')
else:
    DEBUG = False
    print('DJANGO SETTINGS IN PRODUCTION')

LOGGING_LEVEL_MODULE = logging.DEBUG if DEBUG else logging.INFO
ALLOWED_FILES = ['pdf']

LOGIN_URL = '/admin/login/'

# django host and trust
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
    'drf_spectacular',
]

if DEBUG:
    INSTALLED_APPS.append('django_extensions')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Spectacular documentation settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Iago API Documentation',
    'DESCRIPTION': 'Iago is the interface to Jeeny\'s brain',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # OTHER SETTINGS
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
        'v0': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
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
# STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# File storage
# https://django-storages.readthedocs.io/en/1.5.0/index.html
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = 'iago-bucket'
AWS_LOCATION = 'public' # yes all uploads are by default public - this is because for mvp we've decided to not care about security - tbh not my call but whatever
