import os
import re
import paramiko
import tempfile
import time

from haas.models import Instance
from django.db.models import Count
from django.conf import settings


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


    def __get_cmd(self, cmd_name):
        """
        Fetch a defined command string from the ElepHaaS config

        Any commands defined in the COMMANDS configuration variable can be
        fetched with this method. These commands may utilize any one of
        several injected variables:

        * inst: The current instance. Any drill-down is available.
        * version: An array of all version parts, split by '.'.
        * pgdata: The pgdata of the current instance, or herd if no
              local pgdata was set.
        * COMMANDS: The COMMANDS dict itself, in case the user defined
              their own macros.

        :param cmd_name: Name of the configured command to retrieve

        :return: String output of the command, if any, or an empty string.
        """

        full_cmd = ''

        if cmd_name in settings.COMMANDS:
            full_cmd = settings.COMMANDS[cmd_name]

        inst = self.instance

        # Start by injecting any defined macros so they're unrolled before
        # we replace actual variables. Then it's safe to format the instance
        # pgdata, and other provided variables.

        try:
            full_cmd = full_cmd.format(COMMANDS = settings.COMMANDS)
        except KeyError:
            pass

        full_cmd = full_cmd.format(
            inst = inst,
            pgdata = (inst.local_pgdata or inst.herd.pgdata),
            version = inst.version.split('.')
        )

        return full_cmd


    def __run_cmd(self, command):
        """
        Execute a command on this instance's host via SSH

        This is mainly just a wrapper for execute_command that subs the
        host name of the current instance.

        :param command: Full command to execute remotely.

        :raise: Exception output obtained from STDERR, if any.
        :return: String output from the command, if any.
        """

        return execute_remote_cmd(self.instance.server.hostname, command)


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

            # If the metadata isn't up to date and this instance *is* online,
            # we don't want to error out. Just act like it worked.

            try:
                self.__run_cmd(self.__get_cmd('start'))
            except Exception, e:
                if not 'already running' in str(e):
                    raise

        inst.is_online = True
        inst.save()


    def start_backup(self):
        """
        Put a running Postgres instance in backup mode.
        
        This function uses a fast backup start, causing an immediate
        checkpoint. This may cause this function to return after a long pause,
        but this is due to the pg_ctl command waiting for the checkpoint to
        complete.

        This function also uses an ssh connection since that method should
        "always" work without some specialized database superuser.

        :raises: Exception backup mode had problems starting.
        """

        inst = self.instance

        if not inst.is_online:
            return

        try:
            port = inst.herd.db_port
            query = "SELECT pg_start_backup('ElepHaaS', true)"
            self.__run_cmd(
                'psql -p %d -c "%s" postgres' % (port, query)
            )

        except Exception, e:
            # If we can't enter backup mode, that's clearly a problem.
            if not 'not connect' in str(e) and not 'NOTICE:' in str(e):
                raise

            # If we're already in backup mode, this is not a fatal error.
            elif 'already in progress' in str(e):
                pass


    def stop(self):
        """
        Stop this PostgreSQL instance

        :raises: Exception if the instance could not be stopped.
        """
        inst = self.instance

        if inst.is_online:

            # If the metadata isn't up to date and this instance *is not*
            # online, we don't want to error out. Just act like it worked.

            try:
                self.__run_cmd(self.__get_cmd('stop'))
            except Exception, e:
                if not 'not running' in str(e) and not 'not exist' in str(e):
                    raise

        inst.is_online = False
        inst.save()


    def stop_backup(self):
        """
        Take a running Postgres instance out of backup mode.
        
        This function is the analog of start_backup. In Postgres, this simply
        stops the archive log labeling and rotates xlog files generated after
        start_backup was called. This ensures all xlog files to follow the
        master are transferred as a group.

        This function also uses an ssh connection since that method should
        "always" work without some specialized database superuser.

        :raises: Exception backup mode had problems stopping.
        """

        inst = self.instance

        if not inst.is_online:
            return

        try:
            port = inst.herd.db_port
            query = 'SELECT pg_stop_backup()'
            self.__run_cmd(
                'psql -p %d -c "%s" postgres' % (port, query)
            )
        except Exception, e:
            if not 'not connect' in str(e) and not 'NOTICE:' in str(e):
                raise


    def reload(self):
        """
        Reload this PostgreSQL instance

        Essentially this is used to re-read various configuration files.

        :raises: Exception if the instance could not be reloaded.
        """

        inst = self.instance

        if not inst.is_online:
            return

        self.__run_cmd(self.__get_cmd('reload'))


    def master_sync(self):
        """
        Synchronize this instance with its upstream master

        Theoretically we know everything we need about this instance, including
        a master it might be subscribed to. If this function is called, the
        caller wants us to replace the slave with the contents of the
        master, presumably because they are out of sync.

        To make this as fast as possible, we will attempt pg_rewind *first*,
        since that will preclude the need for rsync. If that fails, we will
        revert to synchronizing the data directory from upstream. In that cas,
        we also put the upstream master in backup mode for safe "backup"
        purposes. This ensures the replication stream is as fresh as possible
        since a checkpoint took place before the sync started.

        :raises: Exception if the instance could not be synchronized.
        """

        inst = self.instance

        # If the instance is online, stop it so we don't synchronize open
        # files. That would be bad, Mmmkay? While we're at it, we should
        # only transfer whole files to avoid excessive reads on the slave
        # which can slow down the transfers.

        if inst.is_online:
            self.stop()

        primary_dir = inst.master.local_pgdata or inst.herd.pgdata
        replica_dir = inst.local_pgdata or inst.herd.pgdata

        # Attempt to perform a rewind. This will only work if wal_log_hints
        # was enabled and the server recently diverged from replication stream
        # or is an old primary we're reclaiming, *and* the instance was shut
        # down cleanly. That's a lot of caveats, but if it works, we save a
        # substantial amount of time and resources.

        try:
            rewind = "pg_rewind -D %s"
            rewind += " --source-server='host=%s port=%s dbname=%s user=%s'"

            self.__run_cmd(rewind % (
                replica_dir, inst.herd.vhost, inst.herd.db_port,
                'postgres', 'replication'
            ))

        # If the rewind failed, revert to a standard rsync rebuild of the
        # replica.

        except:

            raise Exception(res)

            master = PGUtility(inst.master)

            xlog_mask = os.path.join('pg_xlog', '*')

            sync = 'rsync -K -a --rsh=ssh -W --delete'
            sync += ' --exclude=recovery.conf'
            sync += ' --exclude=%s'
            sync += ' --exclude=postmaster.*'
            sync += ' postgres@%s:%s %s'

            # Put the master into backup mode before starting the sync. This
            # triggers an implicit checkpoint so all dirty buffers are written
            # before the sync starts.

            master.start_backup()

            self.__run_cmd(sync % (
                xlog_mask, inst.master.server.hostname, primary_dir, 
                os.path.dirname(replica_dir)
            ))

            master.stop_backup()

        # Post sync, we need a new recovery.conf file. There's also a chance 
        # the sync is due to an upstream upgrade, in which case the new
        # datafiles will not match the version of the current instance. So
        # we should copy the version from our primary before continuing.
        # This includes our own instance so methods get correct info.

        self.update_stream_config()
        inst.version = inst.master.version
        inst.save()

        self.instance = inst

        # Include config files. The server might not be in configuration
        # management yet, but still needs them to run. This is a hack to
        # fix Debian-based systems because they separate config files
        # from the pgdata directory. An easy way to "fix" this is to
        # symlink the actual config files into the pgdata directory so
        # they're included in the data dir sync.

        ver = '.'.join(inst.master.version.split('.')[:2])
        conf_dir = os.path.join(
            os.sep, 'etc', 'postgresql', ver, inst.herd.base_name
        )

        sync = 'rsync -a --rsh=ssh postgres@%s:%s %s'

        self.__run_cmd(sync % (
            inst.master.server.hostname, conf_dir, os.path.dirname(conf_dir)
        ))

        # Handle the pg_xlog data separately so we get all of the upstream
        # changes that might have happened during the transfer. go last. This
        # prevents rsync from complaining about missing files since xlog files
        # rotate frequently.

        xlog_dir = os.path.join(primary_dir, 'pg_xlog')

        sync = 'rsync -a --rsh=ssh -W --delete'
        sync += ' postgres@%s:%s %s'

        self.__run_cmd(sync % (
            inst.master.server.hostname, xlog_dir, replica_dir
        ))

        # Once the process is complete, attempt to start the instance. Again,
        # this could fail and we'd go back to our caller with an exception.
        # We should also pause temporarily to allow the replica to "catch up"
        # before returning control to our caller, which may try to query
        # the instance while it's still restoring.

        self.start()

        time.sleep(10)


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

        self.__run_cmd(self.__get_cmd('promote'))

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
        self.update_stream_config()
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

        try:
            masters = Instance.objects.exclude(pk = inst.pk).filter(
                herd_id = inst.herd_id,
                master_id__isnull = True
            ).annotate(sub_count=Count('master_id')).order_by('-sub_count')
            
            return masters[0]

        except IndexError:
            return None


    def get_version(self):
        """
        Get the version of an instance, or detect it if currently unknown.

        Several functions rely on the Postgres version of the instance.
        This function will detect the version from the PG_VERSION file in
        the PGDATA root directory.

        :return: The version of Postgres this instance is running.
        """

        inst = self.instance

        if not inst.version:
            usedir = inst.local_pgdata or inst.herd.pgdata
            ver_file = os.path.join(usedir, 'PG_VERSION')

            inst.version = self.__run_cmd(
                'cat %s' % (ver_file,)
            ).strip()

        return inst.version


    def update_stream_config(self):
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
            'replication', inst.herd.vhost, inst.herd.db_port,
            inst.herd.base_name + '_' + inst.server.hostname
        )

        rec_file.write("standby_mode = 'on'\n")
        rec_file.write("recovery_target_timeline = 'latest'\n")
        rec_file.write("primary_conninfo = '%s'\n" % info)
        self.receive_file(rec_file.name, rec_path)
        rec_file.close()


    def init_missing(self):
        """
        If this instance is missing, attempt to create it.

        When this method is called, we check for the existence of this
        instance on its declared server. If it's not found, we can do
        one of two things:

        * Create a new replica if a master is defined.
        * Otherwise, bootstrap a brand new instance from scratch.

        :raises: Exception in case of instance init failure.
        """

        # Start by trying to find the 'base' directory that is commonly
        # found in an active instance. If we find it *do not run*! We use
        # test to obtain a non-zero exit on failure, which should give
        # us an exception from the command execution subroutine.

        inst = self.instance
        pgdata = inst.local_pgdata or inst.herd.pgdata

        try:
            self.__run_cmd(
                'test -d %s' % (os.path.join(pgdata, 'base'),)
            )
            return
        except:
            pass

        # There is a lot of scaffolding code in place already. We just need
        # to act as a switch to invoke whichever appropriate command is
        # necessary to bootstrap the new instances.

        if inst.master:
            self.master_sync()
        else:
            try:
                self.__run_cmd(self.__get_cmd('init'))
            except Exception, e:

                # If this is a Debian/Ubuntu system, there's a bug when a port
                # is defined that causes error output we need to ignore.
                if 'uninitialized value' in str(e):
                    pass

        # Last but not least, start the instance. Admins can configure from
        # this point, but the instance has been newly allocated as promised.

        self.start()
