import os

from django.contrib import admin, messages
from db_instance.models import DBDR

__all__ = ['DBDRAdmin']

# Database DR Admin Model

class DBDRAdmin(admin.ModelAdmin):
#    actions = ['stop_instances', 'start_instances']
    actions = []
    exclude = ('created_dt', 'modified_dt')
    list_display = ('primary', 'secondary', 'vhost')
    search_fields = ('primary', 'secondary', 'vhost')


#    stop_instances.short_description = "Stop selected PostgreSQL Instances"


admin.site.register(DBDR, DBDRAdmin)
