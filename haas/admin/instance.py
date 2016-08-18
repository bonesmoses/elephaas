from django.contrib import admin, messages
from django.shortcuts import render

import psycopg2
import socket

from haas.models import Instance
from haas.utility import execute_remote_cmd, PGUtility
from haas.admin.base import HAASAdmin

__all__ = ['InstanceAdmin']


class InstanceAdmin(HAASAdmin):
    actions = ['start_instances', 'stop_instances', 'restart_instances',
        'reload_instances', 'promote_instances', 'demote_instances',
        'rebuild_instances',
    ]
    exclude = ('created_dt', 'modified_dt')
    list_display = ('herd', 'get_server', 'get_port', 'version', 
        'is_primary', 'is_online', 'mb_lag'
    )
    list_filter = ('herd', 'herd__environment', 'is_online', 'version')
    search_fields = ('herd__herd_name', 'server__hostname', 'version')
    readonly_fields = ('master', 'version',)


    def mb_lag(self, instance):
        if instance.master:
            mypos = instance.xlog_pos or 0
            masterpos = instance.master.xlog_pos or 0
            return round(abs(masterpos - mypos) / 1024.0 / 1024.0, 2)
    mb_lag.short_description = 'MB Lag'


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
        itself. There can also a backend monitor on each server that will
        keep these values updated, but bootstrapping is always best.

        Autodetected fields:
          * is_online
          * master
          * version
        """

        # First, check the online status. We want this to be as fresh as
        # possible, so we might as well grab it now.

        obj.is_online = False

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        check = sock.connect_ex((obj.server.hostname, obj.herd.db_port))

        if check == 0:
            obj.is_online = True

        # Then, since herds are organized such that each herd follows a single
        # primary node, we can auto-declare that this is a replica or not.
        # If we search and find a primary for this herd, that instance will
        # become our master.

        util = PGUtility(obj)
        obj.master = util.get_herd_primary()
        obj.version = util.get_version()

        # Finally, save now that we've hijacked everything.

        obj.save()


    def start_instances(self, request, queryset):
        """
        Start all transmitted PostgreSQL instances

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

        return render(request, 'admin/haas/instance/rebuild.html', 
                {'queryset' : queryset,
                 'opts': self.model._meta,
                 'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
                }
        )

    rebuild_instances.short_description = "Rebuild Selected Replicas"


    def promote_instances(self, request, queryset):
        """
        Promote transmitted PostgreSQL replication instances to master state
        """

        if request.POST.get('post') == 'yes':

            for inst_id in request.POST.getlist(admin.ACTION_CHECKBOX_NAME):
                inst = Instance.objects.get(pk=inst_id)

                try:
                    util = PGUtility(inst)
                    util.promote()

                except Exception, e:
                    self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                    continue

                self.message_user(request, "%s promoted to read/write!" % inst)
            return

        # Now go to the confirmation form. It's very basic, and only serves
        # to disrupt the process and avoid accidental promotions that would
        # necessitate a resync.

        queryset = queryset.exclude(master_id__isnull=True)

        if queryset.count() < 1:
            self.message_user(request, "No valid replicas to promte!", messages.WARNING)
            return

        return render(request, 'admin/haas/instance/promote.html', 
                {'queryset' : queryset,
                 'opts': self.model._meta,
                 'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
                }
        )

    promote_instances.short_description = "Promote Selected Replicas"


    def demote_instances(self, request, queryset):
        """
        Demote selected instances back into streaming herd replicas

        Given a node is a primary, meaning at one point it was promoted,
        we probably eventually want to convert it back. This encapsulates
        that process and works for several selected primaries.
        
        Instances which are the only primary in the herd are automatically
        pruned from the select list. This check is performed both before 
        *and* after the confirmation form, in case the only masters from
        a single herd are all selected.
        """

        if request.POST.get('post') == 'yes':

            # Iterate through every submitted instance and call the utility
            # to demote each. It should perform the check logic that ensures
            # we always have at least one remaining master in the herd.

            for inst_id in request.POST.getlist(admin.ACTION_CHECKBOX_NAME):
                inst = Instance.objects.get(pk=inst_id)

                #util = PGUtility(inst)
                #result = util.demote()

                try:
                    util = PGUtility(inst)
                    result = util.demote()

                except Exception, e:
                    self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                    continue

                host=inst.server.hostname
                herd=inst.herd
                self.message_user(request, "%s demoted to %s replica!" % (host, herd))
            return

        # For the confirmation piece, we should remove any streaming replicas,
        # because they can't be demoted further.

        queryset = queryset.exclude(master_id__isnull=False)

        # Further, we should remove any primary instances that still have
        # active subscribers. This menu option is not meant for DR failover
        # work. We can use the same loop to verify that at least one other
        # primary would exist if we demoted this one.

        for inst in queryset:
            replicas = Instance.objects.filter(master_id = inst.pk).count()

            if replicas > 0:
                self.message_user(request, "%s has active subscribers!" % 
                    inst.server.hostname,
                    messages.WARNING
                )
                queryset = queryset.exclude(pk=inst.pk)

            masters = Instance.objects.exclude(pk = inst.pk).filter(
                herd_id = inst.herd_id,
                master_id__isnull=True
            ).count()

            if masters < 1:
                self.message_user(request, "%s herd needs at least one master!" % 
                    inst.herd,
                    messages.WARNING
                )
                queryset = queryset.exclude(pk=inst.pk)

        # If after all our prerequisite checks, there are no results, just go
        # back to the previous menu and complain that there was nothing to do.

        if queryset.count() < 1:
            self.message_user(request, "No valid instances to demote!", messages.WARNING)
            return

        return render(request, 'admin/haas/instance/demote.html', 
                {'queryset' : queryset,
                 'opts': self.model._meta,
                 'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
                }
        )

    demote_instances.short_description = "Demote Selected Primary Instances"


    def restart_instances(self, request, queryset):
        """
        Restart all transmitted PostgreSQL instances

        Basicaly we just call for a fast stop followed by a start. Nothing
        complicated here. Unlike stop, we don't skip stopped instances, and
        unline start, we don't skip running ones.
        """

        for inst in queryset:
            try:
                util = PGUtility(inst)
                util.stop()
                util.start()

            except Exception, e:
                self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                continue

            self.message_user(request, "%s restarted!" % inst)

    restart_instances.short_description = "Restart Selected Instances"


    def reload_instances(self, request, queryset):
        """
        Reload all transmitted PostgreSQL instances

        This is provided as a way of reloading configuration files.
        """

        for inst in queryset:
            try:
                util = PGUtility(inst)
                util.reload()

            except Exception, e:
                self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                continue

            self.message_user(request, "%s config files reloaded!" % inst)

    reload_instances.short_description = "Reload Selected Instances"

admin.site.register(Instance, InstanceAdmin)





