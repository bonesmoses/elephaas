from django.contrib import admin
from db_host.models import DBHost

# Register your models here.

class DBHostAdmin(admin.ModelAdmin):
    exclude = ('created_dt', 'modified_dt')
    list_display = ('db_label', 'db_host', 'db_port', 'db_user', 'db_name')
    list_filter = ('db_env',)

admin.site.register(DBHost, DBHostAdmin)
