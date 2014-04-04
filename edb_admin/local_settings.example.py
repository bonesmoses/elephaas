import ldap
ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
from django_auth_ldap.config import LDAPSearch

import logging

logger = logging.getLogger('django_auth_ldap')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

SECRET_KEY = 'zwl#&dyf@-=-&5%6(o0n6)cx^avtjk)b@x!)2tz%_p(k89+upj'

DEBUG = True
TEMPLATE_DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'postgres',
        'HOST': 'localhost',
        'USER': 'postgres',
        'OPTIONS': {
            'options': '-c search_path=edb_admin',
        }
    }
}

AUTHENTICATION_BACKENDS = (
    'django_auth_ldap.backend.LDAPBackend',
)

AUTH_LDAP_SERVER_URI = "ldap://chicagodc.peak6.net"

AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: False,
    ldap.OPT_X_TLS_DEMAND: True,
    ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_NEVER
}

AUTH_LDAP_BIND_DN = ''
AUTH_LDAP_BIND_PASSWORD = ''
AUTH_LDAP_START_TLS = True
AUTH_LDAP_USER_SEARCH = LDAPSearch("ou=DBA,ou=Technology,ou=Shared Services,ou=User Accounts,dc=peak6,dc=net",
    ldap.SCOPE_SUBTREE, '(uid=%(user)s)')
