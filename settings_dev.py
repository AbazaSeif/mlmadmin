from settings import *


DEBUG = True
TEMPLATE_DEBUG = DEBUG

BOOTSTRAP_THEME = 'ubuntu'

AUTH_USE_KERBEROS = False

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

# Automatically create a Token when a user is created
REST_FRAMEWORK_TOKEN_USER_CREATE = True
