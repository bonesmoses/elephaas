from django.contrib import admin, messages
from django import forms

import psycopg2

from haas.models import Environment, Herd, Server, Instance
from haas.utility import execute_remote_cmd

__all__ = ['EnvironmentAdmin', 'HerdAdmin', 'ServerAdmin', 'InstanceAdmin']


class EnvironmentAdmin(admin.ModelAdmin):
    exclude = ('created_dt', 'modified_dt')

admin.site.register(Environment, EnvironmentAdmin)


class HerdAdmin(admin.ModelAdmin):
    exclude = ('created_dt', 'modified_dt')
    list_display = ('herd_name', 'db_port', 'vhost')

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
    exclude = ('created_dt', 'modified_dt')
    list_display = ('hostname', 'environment')
    list_filter = ('environment',)
    form = ServerForm

admin.site.register(Server, ServerAdmin)


class InstanceAdmin(admin.ModelAdmin):
    #actions = ['stop_instances', 'start_instances']
    exclude = ('created_dt', 'modified_dt')
    list_display = ('herd', 'get_server', 'get_port', 'version',
        'is_online'
    )
    list_filter = ('herd', 'herd__environment', 'is_online', 'version')
    search_fields = ('herd__herd_name', 'server__hostname', 'version')
    readonly_fields = ('version',)


    def get_server(self, instance):
        return str(instance.server.hostname)
    get_server.short_description = 'Container'


    def get_port(self, instance):
        return str(instance.herd.db_port)
    get_port.short_description = 'DB Port'


    def save_model(self, request, obj, form, change):
        """
        Automatically detect/populate several fields before saving instance

        Since we're defining what is (hopefully) an existing structure,
        we should be able to auto-detect several elements from the database
        itself. There is also a backend monitor on each server that will
        keep these values updated, but bootstrapping is always best.

        Autodetected fields:
          * is_online
          * version
          * xlog_pos
        """

        conn = None

        # First, check the online status. We want this to be as fresh as
        # possible, so we might as well grab it now.

        try:
            conn = psycopg2.connect(
                host = obj.server.hostname, port = obj.herd.db_port,
                database = 'postgres', user = 'postgres'
            )
            if conn:
                obj.is_online = True
        except:
            obj.is_online = False

        # Now, try to get the database version from the instance.
        # If we can't get the version and this is a replica, set the
        # version to the value used in the primary node.

        if conn:
            cur = conn.cursor()
            cur.execute("SELECT substring(version() from '[\d.]+')")
            obj.version = cur.fetchone()[0]
        elif obj.master:
            obj.version = obj.master.version

        # Now we can get the status of the transaction log position.
        # The backend monitor on each server will keep this updated, but
        # we might as well bootstrap it now.

        SQL = "SELECT pg_current_xlog_location()"
        if obj.master:
            SQL = "SELECT pg_last_xlog_replay_location()"

        if conn:
            cur = conn.cursor()
            cur.execute(SQL)
            obj.xlog_pos = cur.fetchone()[0]

        # Finally, save now that we've hijacked everything.

        obj.save()

admin.site.register(Instance, InstanceAdmin)





