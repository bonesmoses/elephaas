from django.contrib import admin, messages
from django.template import RequestContext  
from django.conf.urls import patterns  
from django.shortcuts import render_to_response, render

import paramiko
from db_instance.models import DBInstance, DBReplica

# Disable the "Delete selected" action. Bad.

admin.site.disable_action('delete_selected')

# Database Instance Admin Model

def etest(arg):
    run('echo %s' % arg)

class DBInstanceAdmin(admin.ModelAdmin):
    actions = ['stop_instances', 'start_instances']
    exclude = ('created_dt', 'modified_dt')
    list_display = ('instance', 'db_host', 'db_port', 'version', 'duty',
        'get_master', 'environment', 'is_online')
    list_filter = ('environment', 'is_online', 'duty')
    search_fields = ('instance', 'db_host', 'db_user', 'version', 'get_master')


    def __run_remote_cmd(self, host, command):
        """
        Execute a command on a remote host via SSH

        For the given host, this function assumes an SSH key is set up between
        both hosts. Given this, we execute the command as-is and return any
        error output, if any. For now, we also assume the postgres system user
        will be running these commands on the remote hosts.

        :param host: Name of host target for desired command.
        :param command: Full command to execute remotely.

        :returns: String output obtained from STDERR, if any.
        """

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username='postgres')
        stdin, stdout, stderr = client.exec_command(command)
        err = stderr.read()

        return err


    def get_master(self, instance):
        return str(instance.master)
    get_master.short_description = 'Master'
    get_master.admin_order_field = 'dbinstance__db_host'


    def stop_instances(self, request, queryset):
        """
        Stop all transmitted PostgreSQL instances

        This function assumes we're running against a bunch of Debian-based
        systems so we can use pg_ctlcluster. Thus far, that's the case. Later
        revisions may change that assumption.

        Skip already stopped services.
        """

        for inst in queryset:
            if not inst.is_online:
                self.message_user(request, "%s is already stopped." % inst,
                    messages.WARNING
                )
                continue

            ver = '.'.join(inst.version.split('.')[:2])

            err = self.__run_remote_cmd(inst.db_host,
                'pg_ctlcluster %s %s stop -m fast' % (ver, inst.instance)
            )

            if err:
                self.message_user(request, "%s : %s" % (err, inst), messages.ERROR)
            else:
                self.message_user(request, "%s stopped!" % inst)
                inst.is_online = False
                inst.save()


    def start_instances(self, request, queryset):
        """
        Start all transmitted PostgreSQL instances

        This function assumes we're running against a bunch of Debian-based
        systems so we can use pg_ctlcluster. Thus far, that's the case. Later
        revisions may change that assumption.

        Skip already running services.
        """

        for inst in queryset:
            if inst.is_online:
                self.message_user(request, "%s is already running." % inst,
                    messages.WARNING
                )
                continue

            ver = '.'.join(inst.version.split('.')[:2])

            err = self.__run_remote_cmd(inst.db_host,
                'pg_ctlcluster %s %s start' % (ver, inst.instance)
            )

            if err:
                self.message_user(request, "%s : %s" % (err, inst), messages.ERROR)
            else:
                self.message_user(request, "%s started!" % inst)
                inst.is_online = True
                inst.save()


    stop_instances.short_description = "Stop selected PostgreSQL Instances"
    start_instances.short_description = "Start selected PostgreSQL Instances"


class DBReplicaAdmin(DBInstanceAdmin):
    actions = ['rebuild_instances']
    #actions = None
    exclude = ('created_dt', 'modified_dt')
    list_display = ('instance', 'db_host', 'db_port', 'duty',
        'get_master')
    list_filter = ('duty',)
    search_fields = ('instance', 'db_host', 'get_master')


    def get_actions(self, request):
        """
        Return our actions, instead of those from our super class.
        """
        actions = super(DBReplicaAdmin, self).get_actions(request)
        del actions['stop_instances']
        del actions['start_instances']
        return actions

#    def get_urls(self):
#        urls = super(DBReplicaAdmin, self).get_urls()
#        my_urls = patterns('',
#            (r'\d+/rebuild/$', self.admin_site.admin_view(self.rebuild_instances)),
#        )
#        return my_urls + urls


    def rebuild_instances(self, request, queryset):
        """
        Rebuild all transmitted PostgreSQL replication instances from master

        """

        if request.POST.get('post') == 'yes':
            inst_list = request.POST.getlist('_selected_action')
            for inst in inst_list:
                self.message_user(request, "%s rebuilt!" % inst)
            return

        # Before presenting the confirmation form, filter out any instances
        # with no master. They can't be rebuilt for a master... duh.

        rebuild_list = []
        obj_list = []

        for inst in queryset:
            if hasattr(inst, 'master'):
                rebuild_list.append('%s (%s)' % (inst, inst.master))
                obj_list.append(inst)
            else:
                self.message_user(request, "%s has no master" % inst)

        if len(rebuild_list) < 1:
            return

        # Now go to the confirmation form. It's very basic, and only serves
        # to disrupt the process and avoid accidental rebuilds.

        return render(request, 'admin/rebuild_confirmation.html', 
                {'obj_list' : obj_list,
                 'opts': self.model._meta,
                 'rebuild_list': rebuild_list }
        )


    rebuild_instances.short_description = "Rebuild selected PostgreSQL Slaves"


admin.site.register(DBInstance, DBInstanceAdmin)
admin.site.register(DBReplica, DBReplicaAdmin)
