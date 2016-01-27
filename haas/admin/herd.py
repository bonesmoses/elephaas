from django.contrib import admin
from haas.models import Herd

__all__ = ['HerdAdmin']

class HerdAdmin(admin.ModelAdmin):
    exclude = ('created_dt', 'modified_dt')
    list_display = ('herd_name', 'db_port', 'vhost')

admin.site.register(Herd, HerdAdmin)
