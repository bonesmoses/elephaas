from django.contrib import admin

from haas.models import Herd
from haas.admin.base import HAASAdmin

__all__ = ['HerdAdmin']

class HerdAdmin(HAASAdmin):
    exclude = ('created_dt', 'modified_dt')
    list_display = ('herd_name', 'db_port', 'vhost')

admin.site.register(Herd, HerdAdmin)
