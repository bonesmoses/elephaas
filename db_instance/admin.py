import os

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


    def _run_remote_cmd(self, host, command):
        """
        Execute a command on a remote host via SSH

        For the given host, this function assumes an SSH key is set up between
        both hosts. Given this, we execute the command as-is and return any
        error output, if any. For now, we also assume the postgres system user
        will be running these commands on the remote hosts.

        :param host: Name of host target for desired command.
        :param command: Full command to execute remotely.

        :raise: Exception output obtained from STDERR, if any.
        """

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username='postgres')
        stdin, stdout, stderr = client.exec_command(command)
        err = stderr.read()

        if err:
            raise Exception(err)


    def get_readonly_fields(self, request, obj=None):
        """
        Don't let admin users change the master from standard menu entries
        """
        if obj:
            return ('master',) + self.readonly_fields
        return self.readonly_fields


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

            try:
                self._run_remote_cmd(inst.db_host,
                    'pg_ctlcluster %s %s stop -m fast' % (ver, inst.instance)
                )

            except Exception, e:
                self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                continue

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

            try:
                self._run_remote_cmd(inst.db_host,
                    'pg_ctlcluster %s %s start' % (ver, inst.instance)
                )

            except Exception, e:
                self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                continue

            self.message_user(request, "%s started!" % inst)
            inst.is_online = True
            inst.save()


    stop_instances.short_description = "Stop selected PostgreSQL Instances"
    start_instances.short_description = "Start selected PostgreSQL Instances"


class DBReplicaAdmin(DBInstanceAdmin):
    actions = ['rebuild_instances', 'promote_instances', 'remaster_instances']
    #actions = None
    exclude = ('created_dt', 'modified_dt')
    list_display = ('instance', 'db_host', 'db_port', 'duty',
        'get_master')
    list_filter = ('duty',)
    search_fields = ('instance', 'db_host', 'get_master')


    def __init__(self,*args,**kwargs):
        """
        This virtual view shouldn't allow deep editing of model items
        """
        super(DBReplicaAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )


    def queryset(self, request):
        """
        Restrict this model to only report slave instances.
        """
        return self.model.objects.exclude(master = None)


    def get_actions(self, request):
        """
        Return our actions, instead of those from our super class.
        """
        actions = super(DBReplicaAdmin, self).get_actions(request)
        del actions['stop_instances']
        del actions['start_instances']
        return actions


    can_delete = False

    def has_add_permission(self, request):
        return False


    def rebuild_instances(self, request, queryset):
        """
        Rebuild all transmitted PostgreSQL replication instances from master

        """

        # If we should be rebuilding an instance, connect to the host,
        # ensure the instance is stopped, and sync the data directories
        # through rsync + ssh.

        if request.POST.get('post') == 'yes':

            for inst_id in request.POST.getlist('_selected_action'):
                inst = DBInstance.objects.get(pk=inst_id)
                ver = '.'.join(inst.version.split('.')[:2])

                try:

                    # If the instance is online, stop it and mark it as such.
                    # Subsequent commands may fail and if the instance can't
                    # be restarted, listing it as running would be wrong.

                    if inst.is_online:
                        self._run_remote_cmd(inst.db_host,
                            'pg_ctlcluster %s %s stop -m fast' % (
                                ver, inst.instance
                            )
                        )
                        inst.is_online = False
                        inst.save()

                    sync = 'rsync -a --rsh=ssh --exclude=recovery.conf'
                    sync += ' --exclude=postmaster.*'
                    sync += ' --delete postgres@%s:%s/ %s'

                    self._run_remote_cmd(inst.db_host, sync % (
                        inst.master.db_host, inst.master.pgdata, inst.pgdata
                    ))

                    # Once the process is complete, attempt to start the
                    # instance. A lot can go wrong with this type of
                    # rebuild, so don't just assume it worked.

                    self._run_remote_cmd(inst.db_host,
                        'pg_ctlcluster %s %s start' % (
                            ver, inst.instance
                        )
                    )

                    inst.is_online = True
                    inst.save()

                except Exception, e:
                    self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                    continue

                self.message_user(request, "%s rebuilt!" % inst)
            return

        # Now go to the confirmation form. It's very basic, and only serves
        # to disrupt the process and avoid accidental rebuilds.

        rebuild_list = ['%s (%s)' % (inst, inst.master) for inst in queryset]

        return render(request, 'admin/rebuild_confirmation.html', 
                {'queryset' : queryset,
                 'opts': self.model._meta,
                 'rebuild_list': rebuild_list }
        )


    rebuild_instances.short_description = "Rebuild Selected Replicas"


    def promote_instances(self, request, queryset):
        """
        Promote transmitted PostgreSQL replication instances to master state

        """

        if request.POST.get('post') == 'yes':

            for inst_id in request.POST.getlist('_selected_action'):
                inst = DBInstance.objects.get(pk=inst_id)
                ver = '.'.join(inst.version.split('.')[:2])

                try:
                    # Once the instance has been promoted, it's no longer a
                    # slave. Erase the master and update the role.

                    self._run_remote_cmd(inst.db_host,
                        'pg_ctlcluster %s %s promote' % (
                            ver, inst.instance
                        )
                    )

                    inst.duty = 'master'
                    inst.master = None
                    inst.save()

                except Exception, e:
                    self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                    continue

                self.message_user(request, "%s promoted to read/write!" % inst)
            return

        # Now go to the confirmation form. It's very basic, and only serves
        # to disrupt the process and avoid accidental promotions that would
        # necessitate a resync.

        promote_list = ['%s (%s)' % (inst, inst.master) for inst in queryset]

        return render(request, 'admin/promote_confirmation.html', 
                {'queryset' : queryset,
                 'opts': self.model._meta,
                 'promote_list': promote_list }
        )


    promote_instances.short_description = "Promote Selected Replicas"



    def remaster_instances(self, request, queryset):
        """
        Change the master for transmitted PostgreSQL replicas

        """

        if request.POST.get('post') == 'yes' and request.POST.get('master'):

            master = DBInstance.objects.get(pk=request.POST.get('master'))

            # Iterate through every submitted instance. We'll need to change
            # the recovery.conf to use the new master target, and also reload
            # configuration files to commit the change.

            for inst_id in request.POST.getlist('_selected_action'):
                inst = DBInstance.objects.get(pk=inst_id)
                old_master = inst.master.db_host
                old_port = inst.master.db_port
                ver = '.'.join(inst.version.split('.')[:2])

                try:

                    self._run_remote_cmd(inst.db_host,
                        "sed -i.bak 's/%s/%s/; s/%s/%s/;' %s" % (
                            old_master, master.db_host,
                            old_port, master.db_port,
                            os.path.join(inst.pgdata, 'recovery.conf')
                        )
                    )

                    self._run_remote_cmd(inst.db_host,
                        'pg_ctlcluster %s %s reload' % (
                            ver, inst.instance
                        )
                    )

                    inst.master = master
                    inst.save()

                except Exception, e:
                    self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                    continue

                self.message_user(request, "%s assigned to new master!" % inst)
            return

        # Now go to the confirmation form. The only form item we want to
        # present is the master being selected. While we're here, we should
        # also disable the ability to add new hosts, which shouldn't apply
        # from this menu.

        promote_list = ['%s (%s)' % (inst, inst.master) for inst in queryset]
        useform = self.get_form(request)
        master = useform.base_fields['master']
        master.widget.can_add_related = False

        return render(request, 'admin/remaster.html', 
                {'queryset' : queryset,
                 'opts': self.model._meta,
                 'promote_list': promote_list,
                 'form': useform }
        )


    remaster_instances.short_description = "Change Master for Selected Replicas"

admin.site.register(DBInstance, DBInstanceAdmin)
admin.site.register(DBReplica, DBReplicaAdmin)
