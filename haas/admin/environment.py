from django.contrib import admin

from haas.models import Environment

__all__ = ['EnvironmentAdmin']

class EnvironmentAdmin(admin.ModelAdmin):
    exclude = ('created_dt', 'modified_dt')

admin.site.register(Environment, EnvironmentAdmin)
