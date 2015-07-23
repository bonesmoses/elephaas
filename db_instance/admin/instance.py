import paramiko

from django.contrib import admin, messages
from db_instance.models import DBInstance
from db_instance.admin.base import PGUtility

__all__ = ['DBInstanceAdmin']

# Database Instance Admin Model

class DBInstanceAdmin(admin.ModelAdmin):
    actions = ['stop_instances', 'start_instances']
    exclude = ('created_dt', 'modified_dt')
    list_display = ('instance', 'db_host', 'db_port', 'version', 'duty',
        'get_master', 'environment', 'is_online')
    list_filter = ('environment', 'is_online', 'duty')
    search_fields = ('instance', 'db_host', 'db_user', 'version', 'get_master')


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

            try:
                util = PGUtility(inst)
                util.stop()

            except Exception, e:
                self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                continue

            self.message_user(request, "%s stopped!" % inst)


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


    stop_instances.short_description = "Stop selected PostgreSQL Instances"
    start_instances.short_description = "Start selected PostgreSQL Instances"


admin.site.register(DBInstance, DBInstanceAdmin)
