from django.contrib import admin
from db_instance.models import DBInstance

# Register your models here.

class DBInstanceAdmin(admin.ModelAdmin):
    exclude = ('created_dt', 'modified_dt')
    list_display = ('instance', 'db_host', 'db_port', 'version', 'duty', 'master_host', 'environment', 'is_online')
    list_filter = ('environment', 'is_online', 'duty')
    search_fields = ('instance', 'db_host', 'db_user', 'version')

admin.site.register(DBInstance, DBInstanceAdmin)
