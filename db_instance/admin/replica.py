import tempfile

from django.contrib import admin, messages
from django.shortcuts import render

from db_instance.models import DBReplica
from db_instance.admin import DBInstanceAdmin
from db_instance.admin.base import PGUtility

__all__ = ['DBReplicaAdmin']

# Database Replica Admin Model

class DBReplicaAdmin(DBInstanceAdmin):
    actions = ['rebuild_instances', 'promote_instances', 'remaster_instances']
    exclude = ('created_dt', 'modified_dt')
    list_display = ('instance', 'db_host', 'db_port', 'duty',
        'get_master', 'is_online')
    list_filter = ('environment', 'duty', 'version')
    search_fields = ('instance', 'db_host', 'master__instance',
        'master__db_host')

    can_delete = False


    def __init__(self,*args,**kwargs):
        """
        This virtual view shouldn't allow deep editing of model items
        """
        super(DBReplicaAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = ()


    def get_actions(self, request):
        """
        Return our actions, instead of those from our super class.
        """
        actions = super(DBReplicaAdmin, self).get_actions(request)
        del actions['delete_selected']
        del actions['stop_instances']
        del actions['start_instances']
        return actions


    def has_add_permission(self, request):
        """
        Disable the ability to add new "replicas" since this is a proxy
        """
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
                inst = DBReplica.objects.get(pk=inst_id)

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

        return render(request, 'admin/rebuild_confirmation.html', 
                {'queryset' : queryset,
                 'opts': self.model._meta }
        )


    rebuild_instances.short_description = "Rebuild Selected Replicas"


    def promote_instances(self, request, queryset):
        """
        Promote transmitted PostgreSQL replication instances to master state
        """

        if request.POST.get('post') == 'yes':

            for inst_id in request.POST.getlist('_selected_action'):
                inst = DBReplica.objects.get(pk=inst_id)

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

        promote_list = ['%s (%s)' % (inst, inst.master) for inst in queryset]

        return render(request, 'admin/promote_confirmation.html', 
                {'queryset' : queryset,
                 'opts': self.model._meta }
        )


    promote_instances.short_description = "Promote Selected Replicas"


    def remaster_instances(self, request, queryset):
        """
        Change the master for transmitted PostgreSQL replicas

        """

        if request.POST.get('post') == 'yes' and request.POST.get('master'):

            master = DBReplica.objects.get(pk=request.POST.get('master'))

            # Iterate through every submitted instance. We'll need to change
            # the recovery.conf to use the new master target, and also reload
            # configuration files to commit the change.

            for inst_id in request.POST.getlist('_selected_action'):
                inst = DBReplica.objects.get(pk=inst_id)

                try:
                    util = PGUtility(inst)
                    util.change_master(master)

                except Exception, e:
                    self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                    continue

                self.message_user(request, "%s assigned to new master!" % inst)
            return

        # Now go to the confirmation form. The only form item we want to
        # present is the master being selected. While we're here, we should
        # also disable the ability to add new hosts, which shouldn't apply
        # from this menu.

        useform = self.get_form(request)
        master = useform.base_fields['master']
        master.queryset = master.queryset.filter(duty = 'master')
        master.widget.can_add_related = False

        return render(request, 'admin/remaster.html', 
                {'queryset' : queryset,
                 'opts': self.model._meta,
                 'form': useform }
        )


    remaster_instances.short_description = "Change Master for Selected Replicas"

admin.site.register(DBReplica, DBReplicaAdmin)
