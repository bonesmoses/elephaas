from django.contrib import admin, messages
import paramiko
from db_instance.models import DBInstance

# Database Instance Admin Model

def etest(arg):
    run('echo %s' % arg)

class DBInstanceAdmin(admin.ModelAdmin):
    actions = ['stop_instances', 'start_instances']
    exclude = ('created_dt', 'modified_dt')
    list_display = ('instance', 'db_host', 'db_port', 'version', 'duty',
        'master_host', 'environment', 'is_online')
    list_filter = ('environment', 'is_online', 'duty')
    search_fields = ('instance', 'db_host', 'db_user', 'version', 'master_host')


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


admin.site.register(DBInstance, DBInstanceAdmin)
