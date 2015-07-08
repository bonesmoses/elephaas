
SECRET_KEY = ''

DEBUG = True
TEMPLATE_DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'admin',
        'HOST': 'localhost',
        'USER': 'postgres',
        'OPTIONS': {
            'options': '-c search_path=utility',
        }
    }
}

AUTH_LDAP_BIND_DN = 'pgsql_ldap'
AUTH_LDAP_BIND_PASSWORD = ''
AUTH_LDAP_START_TLS = True
