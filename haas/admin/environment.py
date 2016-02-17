from django.contrib import admin

from haas.models import Environment
from haas.admin.base import HAASAdmin

__all__ = ['EnvironmentAdmin']

class EnvironmentAdmin(HAASAdmin):
    exclude = ('created_dt', 'modified_dt')

admin.site.register(Environment, EnvironmentAdmin)
