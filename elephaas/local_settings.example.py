
SECRET_KEY = ''
PUBLIC_KEY = 'SSH-based public key hash'

DEBUG = True

COMMANDS = {
    'base': 'pg_ctlcluster {version[0]}.{version[1]} {inst.herd.base_name}',
    'start': '{COMMANDS[base]} start',
    'stop': '{COMMANDS[base]} stop -m fast',
    'reload': '{COMMANDS[base]} reload',
    'promote': '{COMMANDS[base]} promote',
}

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

# This is an example of LDAP auth for a corporate installation.
# Uncomment this and customize to activate. Also uncomment the LDAP auth
# method in settings.py to enable the module.
# It might be a good idea to have an LDAP expert handy.

"""
import ldap
import logging

from django_auth_ldap.config import LDAPSearch, GroupOfNamesType

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
logger = logging.getLogger('django_auth_ldap')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

AUTH_LDAP_BIND_DN = 'ldap_user'
AUTH_LDAP_BIND_PASSWORD = 'ldap_password'

AUTH_LDAP_SERVER_URI = "ldap://ldap_host.com"
AUTH_LDAP_REQUIRE_GROUP = "cn=Group,OU=Organization,OU=Path,OU=Groups,DC=Company,DC=com"

AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: False,
    ldap.OPT_X_TLS_DEMAND: True,
    ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_NEVER
}

AUTH_LDAP_CACHE_GROUPS = True
AUTH_LDAP_GROUP_CACHE_TIMEOUT = 300

AUTH_LDAP_START_TLS = True

AUTH_LDAP_USER_SEARCH = LDAPSearch("ou=Group,ou=User,ou=Search,dc=Company,dc=com",
    ldap.SCOPE_SUBTREE, '(uid=%(user)s)')

AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    "is_active": AUTH_LDAP_REQUIRE_GROUP,
    "is_staff": AUTH_LDAP_REQUIRE_GROUP,
    "is_superuser": AUTH_LDAP_REQUIRE_GROUP
}

AUTH_LDAP_GROUP_SEARCH = LDAPSearch("ou=groups,dc=Company,dc=com",
    ldap.SCOPE_SUBTREE, "(objectClass=groupOfNames)"
)
AUTH_LDAP_GROUP_TYPE = GroupOfNamesType(name_attr='cn')
"""
