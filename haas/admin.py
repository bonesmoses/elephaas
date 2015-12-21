from django.contrib import admin
from haas.models import Environment

__all__ = ['EnvironmentAdmin']

# Database Instance Admin Model

class EnvironmentAdmin(admin.ModelAdmin):
    #actions = ['stop_instances', 'start_instances']
    exclude = ('created_dt', 'modified_dt')
    #list_display = ('instance', 'db_host', 'db_port', 'version', 'duty',
    #    'get_master', 'environment', 'is_online')
    #list_filter = ('environment', 'is_online', 'duty', 'version')
    #search_fields = ('instance', 'db_host', 'db_user', 'version',
    #    'master__instance', 'master__db_host')

admin.site.register(Environment, EnvironmentAdmin)
