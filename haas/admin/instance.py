from django.contrib import admin, messages
from django.shortcuts import render

import psycopg2

from haas.models import Instance
from haas.utility import execute_remote_cmd, PGUtility

__all__ = ['InstanceAdmin']


class InstanceAdmin(admin.ModelAdmin):
    actions = ['stop_instances', 'start_instances', 'rebuild_instances']
    exclude = ('created_dt', 'modified_dt')
    list_display = ('herd', 'get_server', 'get_port', 'version', 
        'is_primary', 'is_online'
    )
    list_filter = ('herd', 'herd__environment', 'is_online', 'version')
    search_fields = ('herd__herd_name', 'server__hostname', 'version')
    readonly_fields = ('master', 'version',)


    def is_primary(self, instance):
        return False if instance.master else True
    is_primary.short_description = 'Primary'
    is_primary.boolean = True


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

        # Then, since herds are organized such that each herd follows a single
        # primary node, we can auto-declare that this is a replica or not.
        # If we search and find a primary for this herd, that instance will
        # become our master.

        try:
            primary = Instance.objects.get(herd_id = obj.herd, master_id = None)
            obj.master = primary
            obj.version = primary.version
        except:
            pass

        # Finally, save now that we've hijacked everything.

        obj.save()


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

            try:
                util = PGUtility(inst)
                util.start()

            except Exception, e:
                self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                continue

            self.message_user(request, "%s started!" % inst)

    start_instances.short_description = "Start Selected Instances"


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

            try:
                util = PGUtility(inst)
                util.stop()

            except Exception, e:
                self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                continue

            self.message_user(request, "%s stopped!" % inst)

    stop_instances.short_description = "Stop Selected Instances"


    def rebuild_instances(self, request, queryset):
        """
        Rebuild all transmitted PostgreSQL replication instances from master
        """

        # If we should be rebuilding an instance, connect to the host,
        # ensure the instance is stopped, and sync the data directories
        # through rsync + ssh.

        if request.POST.get('post') == 'yes':

            for inst_id in request.POST.getlist(admin.ACTION_CHECKBOX_NAME):
                inst = Instance.objects.get(pk=inst_id)

                try:
                    util = PGUtility(inst)
                    util.master_sync()

                except Exception, e:
                    self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                    continue

                self.message_user(request, "%s rebuilt!" % inst)
            return

        # Now go to the confirmation form. It's very basic, and only serves
        # to disrupt the process and avoid accidental rebuilds.

        return render(request, 'admin/haas/instance/rebuild_confirmation.html', 
                {'queryset' : queryset,
                 'opts': self.model._meta,
                 'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
                }
        )

    rebuild_instances.short_description = "Rebuild Selected Replicas"


admin.site.register(Instance, InstanceAdmin)





