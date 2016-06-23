# Project settings
PROJECT_ROOT = '/opt/mlmadmin'
MLMADMIN_VERSION = '1.0.1'
MLMMJ_BIN_DIR = '/usr/bin'
MLMMJ_SPOOL_DIR = '/var/spool/mlmmj'
MLMMJ_SPOOL_CHOWN_USER = 'nobody'
MLMMJ_ADMIN_EMAIL = 'postmaster'
MLMMJ_TEXTPATHDEF = '/usr/share/mlmmj/text.skel/en'
COMPANY_NAME = 'My Company' # leave empty to not display the company name
COMPANY_MAIL_DOMAIN = 'example.com'
BOOTSTRAP_THEME = 'ubuntu'

# Use AUTHENTICATION BACKEND 'mlmadmin.auth.backends.MLMRemoteUserBackend'
AUTH_USE_KERBEROS = True

# LDAP settings for AUTHENTICATION BACKEND 'mlmadmin.auth.backends.MLMRemoteUserBackend'
AUTH_LDAP_SERVER_URI_SET = ['ldap1.example.com', 'ldap2.example.com', ]
AUTH_LDAP_BIND_DN = 'CN=ldapuser,OU=USERS,DC=example,DC=com'
AUTH_LDAP_BIND_PASSWORD = 'password'
AUTH_LDAP_USER_SEARCH = 'DC=example,DC=com'
AUTH_LDAP_GROUP_SEARCH = 'OU=MLMAdmin,DC=example,DC=com'
# Put here the users who can be moderators independent of LDAP groups
MLM_SUPERUSERS = ['root', 'admin', ]
# path to the file to store info on synchronization of users and groups
LOG_FILE_SYNC = '/var/log/mlmadmin_sync.log'

# set flags 'is_staff' and 'is_superuser' via LDAP groups
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    'is_staff': ['mlm_staff', 'CN=mlm_staff,%s' % AUTH_LDAP_GROUP_SEARCH],
    'is_superuser': ['mlm_superuser', 'CN=mlm_superuser,%s' % AUTH_LDAP_GROUP_SEARCH],
}

# put in the list 'SETTINGS_EXPORT' those variables that you want to use in templates
# more info: https://github.com/jakubroztocil/django-settings-export
SETTINGS_EXPORT = [
    'COMPANY_NAME',
    'COMPANY_MAIL_DOMAIN',
    'MLMADMIN_VERSION',
    'AUTH_USE_KERBEROS',
    'BOOTSTRAP_THEME',
]

# Automatically create a Token when a user is created
REST_FRAMEWORK_TOKEN_USER_CREATE = False


# Django settings for mlmadmin project.

#DEBUG = True
#TEMPLATE_DEBUG = DEBUG

SERVER_EMAIL = 'mlmadmin@example.com'
DEFAULT_FROM_EMAIL = SERVER_EMAIL

ADMINS = (
    ('jsmith', 'jsmith@example.com'),
)
USE_TZ = True
MANAGERS = ADMINS
SESSION_COOKIE_AGE = 86400
FILE_UPLOAD_TEMP_DIR='/tmp'
FILE_UPLOAD_HANDLERS = ('django.core.files.uploadhandler.TemporaryFileUploadHandler',)

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME':     'mlmadmin',                 # Or path to database file if using sqlite3.
        'USER':     'mlmadmin_dbuser',          # Not used with sqlite3.
        'PASSWORD': 'rGgMBNJJrLOA',             # Not used with sqlite3.
        'HOST':     'localhost',                # Set to empty string for localhost. Not used with sqlite3.
        'PORT':     '',                         # Set to empty string for default. Not used with sqlite3.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.4/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['mlmadmin', 'mlmadmin.example.com']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Moscow'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'ru-RU'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = '%s/media/' % PROJECT_ROOT

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute and relative paths to the upload directory (used in mlmadmin.views.SList)
MEDIA_UPLOAD_ROOT = '%supload/' % MEDIA_ROOT
MEDIA_UPLOAD_URL = '%supload/' % MEDIA_URL

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = '%s/static/' % PROJECT_ROOT

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
#SECRET_KEY = '!$yps2mu^*zt)(&amp;!+9bvw-+-x&amp;!yh$toh2q6-t$jui7v4(1he#'

# https://gist.github.com/ndarville/3452907
try:
    SECRET_KEY
except NameError:
    import os
    SECRET_FILE = os.path.join(PROJECT_ROOT, 'secret.txt')
    try:
        SECRET_KEY = open(SECRET_FILE).read().strip()
    except IOError:
        try:
            import random
            SECRET_KEY = ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(58)])
            secret = open(SECRET_FILE, 'w')
            secret.write(SECRET_KEY)
            secret.close()
        except IOError:
            Exception('Please create a %s file with random characters \
                       to generate your secret key!' % SECRET_FILE)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

AUTHENTICATION_BACKENDS = [
    #'django.contrib.auth.backends.RemoteUserBackend',
    'django.contrib.auth.backends.ModelBackend',
]
if AUTH_USE_KERBEROS:
    AUTHENTICATION_BACKENDS.append('mlmadmin.auth.backends.MLMRemoteUserBackend')

ROOT_URLCONF = 'urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    #'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'rest_framework',
    'rest_framework.authtoken',
    'mlmadmin',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'django_settings_export.settings_export',
)

MESSAGE_STORAGE = 'django.contrib.messages.storage.fallback.FallbackStorage'


REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_AUTHENTICATION_CLASSES': [
        #'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAdminUser',
    ],
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
}
