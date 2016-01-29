import os
import re
import paramiko
import tempfile

from haas.models import Instance
from django.db.models import Count

__all__ = ['execute_remote_cmd', 'PGUtility']

def execute_remote_cmd(hostname, command):
    """
    Execute a command on a host via SSH

    We execute the command as-is and return any error output, if any.
    For now, we also assume the postgres system user will be running
    these commands on the remote hosts.

    :param command: Full command to execute remotely.

    :raise: Exception output obtained from STDERR, if any.
    """

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, username='postgres')
    stdin, stdout, stderr = client.exec_command(command)
    err = stderr.read()
    client.close()

    if err:
        raise Exception(err)
    elif stdout.channel.recv_exit_status() > 0:
        raise Exception(stdout.read())

    return stdout.read()


class PGUtility():
    """
    Utility class for managing PostgreSQL instances within Django

    Several shared operations, such as SSH actions, file copying, instance
    querying, and so on, are common enough they should be in a central
    location. This class can and should be used by Django admin classes
    to accomplish various goals.
    
    For this system to work properly, an SSH key must exist between an
    instance host and wherever this tool is running.
    """

    instance = None

    def __init__(self, instance):
        """
        Initialize an admin utility

        Currently, the utility class acts as an admin wrapper for the instance
        model. Actions must always affect an instance in some way.
        
        :param instance: Django instance model to tie to admin actions.
        """
        self.instance = instance


    def __run_cmd(self, command):
        """
        Execute a command on this instance's host via SSH

        This is mainly just a wrapper for execute_command that subs the
        host name of the current instance.

        :param command: Full command to execute remotely.

        :raise: Exception output obtained from STDERR, if any.
        """

        return execute_remote_cmd(self.instance.server.hostname, command)


    def __build_stream_config(self):
        """
        Build a recovery.conf for the master of this instance.

        For a streaming replica in Postgres to work, it must have a
        recovery.conf file detailing the upstream master connection
        parameters. This method ensures the file follows standard
        conventions across this application.

        :raises: Exception in case of recovery.conf upload problems.
        """

        inst = self.instance
        ver = '.'.join(inst.version.split('.')[:2])

        # Write out a local recovery.conf we can transmit to the instance.
        # Doing it this way is a lot easier than trying to escape everything
        # and sending it via SSH commands.

        usedir = inst.local_pgdata or inst.herd.pgdata
        rec_file = tempfile.NamedTemporaryFile(bufsize=0)
        rec_path = os.path.join(usedir, 'recovery.conf')

        info = 'user=%s host=%s port=%s application_name=%s' % (
            'replication', inst.master.server.hostname, inst.herd.db_port,
            inst.herd.herd_name + '_' + inst.server.hostname
        )

        rec_file.write("standby_mode = 'on'\n")
        rec_file.write("primary_conninfo = '%s'\n" % info)
        self.receive_file(rec_file.name, rec_path)
        rec_file.close()


    def receive_file(self, source, dest):
        """
        Transmit a file to a remote host via SSH

        We transmit the indicated file to the target location. Any errors
        are simply passed along. In addition, the postgres system user is
        currently assumed as the target file owner.

        :param source: Name of file to send to indicated host.
        :param dest: Full path on host to send file.

        :raise: Exception output obtained from secure transmission, if any.
        """

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.instance.server.hostname, username='postgres')
        sftp = client.open_sftp()
        sftp.put(source, dest)
        sftp.close()
        client.close()


    def start(self):
        """
        Start this PostgreSQL instance

        :raises: Exception if the instance could not be started.
        """

        inst = self.instance

        if not inst.is_online:
            ver = '.'.join(inst.version.split('.')[:2])
            self.__run_cmd(
                'pg_ctlcluster %s %s start' % (ver, inst.herd.herd_name)
            )

        inst.is_online = True
        inst.save()


    def stop(self):
        """
        Stop this PostgreSQL instance

        :raises: Exception if the instance could not be stopped.
        """
        inst = self.instance

        if inst.is_online:
            ver = '.'.join(inst.version.split('.')[:2])
            self.__run_cmd(
                'pg_ctlcluster %s %s stop -m fast' % (ver, inst.herd.herd_name)
            )

        inst.is_online = False
        inst.save()


    def reload(self):
        """
        Reload this PostgreSQL instance

        Essentially this is used to re-read various configuration files.

        :raises: Exception if the instance could not be reloaded.
        """

        inst = self.instance

        if not inst.is_online:
            return

        ver = '.'.join(inst.version.split('.')[:2])
        self.__run_cmd(
            'pg_ctlcluster %s %s reload' % (ver, inst.herd.herd_name)
        )


    def master_sync(self):
        """
        Synchronize this instance with its upstream master

        Theoretically we know everything we need about this instance, including
        a master it might be subscribed to. If this function is called, the
        caller wants us to replace the slave with the contents of the
        master, presumably because they are out of sync.

        :raises: Exception if the instance could not be synchronized.
        """

        inst = self.instance

        # If the instance is online, stop it so we don't synchronize open
        # files. That would be bad, Mmmkay? While we're at it, we should
        # only transfer whole files to avoid excessive reads on the slave
        # which can slow down the transfers.

        if inst.is_online:
            self.stop()

        self.__build_stream_config()

        sync = 'rsync -a --rsh=ssh -W --delete'
        sync += ' --exclude=recovery.conf'
        sync += ' --exclude=pg_xlog/*'
        sync += ' --exclude=postmaster.*'
        sync += ' postgres@%s:%s/ %s'

        primary_dir = inst.master.local_pgdata or inst.herd.pgdata
        replica_dir = inst.local_pgdata or inst.herd.pgdata

        self.__run_cmd(sync % (
            inst.master.server.hostname, primary_dir, replica_dir
        ))

        # Handle the pg_xlog data separately so we get all of the upstream
        # changes that might have happened during the transfer. go last. This
        # prevents rsync from complaining about missing files since xlog files
        # rotate frequently.

        sync = 'rsync -a --rsh=ssh -W --delete'
        sync += ' postgres@%s:%s/pg_xlog %s'

        self.__run_cmd(sync % (
            inst.master.server.hostname, primary_dir, replica_dir
        ))

        # Once the process is complete, attempt to start the instance. Again,
        # this could fail and we'd go back to our caller with an exception.

        self.start()


    def promote(self):
        """
        Promote this instance to read/write state

        In the case where an instance is a replica, it is read-only. This
        operation will bring the system up in a fully online state, as if
        it were an upstream master. Doing this also erases the current
        master, since replicatino is no longer in place.

        :raises: Exception if the instance could not be promoted.
        """

        inst = self.instance
        ver = '.'.join(inst.version.split('.')[:2])

        self.__run_cmd(
            'pg_ctlcluster %s %s promote' % (ver, inst.herd.herd_name)
        )

        inst.master = None
        inst.save()


    def demote(self):
        """
        Revert a primary to replica status

        Demoting an instance means:
        
        * Stopping the instance, if running.
        * Assigning it to another primary.
        * Syncing the contents.
        * Starting it up.
        
        We're basically just chaining creation of recovery.conf and calling
        master_sync. Before we do that, we need to find the primary with
        subscribers. We do this mostly because this tool doesn't yet
        support replica chaining.

        :raises: Exception if the instance could not be demoted.
        """

        inst = self.instance

        # Before we do *anything*, make sure we're not demoting the only
        # primary in this herd. That would be extremely bad.

        masters = Instance.objects.exclude(pk = inst.pk).filter(
            herd_id = inst.herd_id,
            master_id__isnull=True
        ).count()

        if masters < 1:
            raise Exception('Will not demote the last available master.')

        # Now we should find the new master, rebuild the config, and sync
        # the contents to follow the chosen master. We save first because
        # the decision was made. If the config or sync failed, we should
        # try those again separately, or manually.

        self.instance.master = self.get_herd_primary()
        self.instance.save()
        self.__build_stream_config()
        self.master_sync()


    def get_herd_primary(self):
        """
        Get the primary for the herd of which this instance is a member

        This utility doesn't yet support master chaining. As such, we take
        our current herd and find all masters and their subscriber counts.
        This guarantees at least one result, provided a primary exists.
        Once we have that, we only need the top result if multiple rows
        match. This ensures newly promoted replicas don't get assigned
        as masters to new instances. At least, not accidentally.

        :return: An instance object for this herd's primary instance.
        """

        inst = self.instance

        master = Instance.objects.exclude(pk = inst.pk).filter(
            herd_id = inst.herd_id,
            master_id__isnull=True
        ).annotate(sub_count=Count('master_id')).order_by('-sub_count')[0]

        return master

