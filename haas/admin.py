from django.contrib import admin, messages
from django import forms

from haas.models import Environment, Herd, Server
from haas.utility import execute_remote_cmd

__all__ = ['EnvironmentAdmin', 'HerdAdmin']


class EnvironmentAdmin(admin.ModelAdmin):
    #actions = ['stop_instances', 'start_instances']
    exclude = ('created_dt', 'modified_dt')
    #list_display = ('instance', 'db_host', 'db_port', 'version', 'duty',
    #    'get_master', 'environment', 'is_online')
    #list_filter = ('environment', 'is_online', 'duty', 'version')
    #search_fields = ('instance', 'db_host', 'db_user', 'version',
    #    'master__instance', 'master__db_host')

admin.site.register(Environment, EnvironmentAdmin)


class HerdAdmin(admin.ModelAdmin):
    #actions = ['stop_instances', 'start_instances']
    exclude = ('created_dt', 'modified_dt')
    list_display = ('herd_name', 'db_port', 'vhost')
    #list_filter = ('environment', 'is_online', 'duty', 'version')
    #search_fields = ('instance', 'db_host', 'db_user', 'version',
    #    'master__instance', 'master__db_host')

admin.site.register(Herd, HerdAdmin)


class ServerForm(forms.ModelForm):
    def clean_hostname(self):
        """
        Check that the supplied hostname has our public key for SSH
        
        Since this tool needs SSH access, the public key in the add/change
        page needs to be in .ssh/authorized_keys. Try to connect to the
        server, and if we fail, don't let the user save this server.
        """
        server = self.cleaned_data['hostname']
        try:
            execute_remote_cmd(server, 'echo Hello World')
        except:
            raise forms.ValidationError("Can't connect to %s!" % server)

        return self.cleaned_data['hostname']


class ServerAdmin(admin.ModelAdmin):
    #actions = ['stop_instances', 'start_instances']
    exclude = ('created_dt', 'modified_dt')
    list_display = ('hostname', 'environment')
    list_filter = ('environment',)
    #search_fields = ('instance', 'db_host', 'db_user', 'version',
    #    'master__instance', 'master__db_host')
    form = ServerForm

admin.site.register(Server, ServerAdmin)







