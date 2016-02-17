from django.contrib import admin
from django import forms

from haas.models import Server
from haas.utility import execute_remote_cmd
from haas.admin.base import HAASAdmin

__all__ = ['ServerAdmin']


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


class ServerAdmin(HAASAdmin):
    exclude = ('created_dt', 'modified_dt')
    list_display = ('hostname', 'environment')
    list_filter = ('environment',)
    form = ServerForm

admin.site.register(Server, ServerAdmin)
