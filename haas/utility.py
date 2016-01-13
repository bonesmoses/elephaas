import os
import re
import paramiko
import tempfile

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

        return execute_remote_cmd(self.instance.db_host, command)


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
        client.connect(self.instance.db_host, username='postgres')
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
                'pg_ctlcluster %s %s start' % (ver, inst.instance)
            )

        inst.is_online = True
        inst.save()


    def get_xlog_location(self):
        """
        For a master system, get its current xlog location.

        This is generally only useful when trying to figure out how far
        behind a replica might be. We use the pg_current_xlog_location
        function to get this value so it can be sent to any number of
        slaves to calculate replication drift.
        
        :return: A Postgres xlog location or None.
        """

        inst = self.instance

        if inst.duty != 'master':
            return None

        try:
            SQL = "SELECT pg_current_xlog_location()"
            loc = self.__run_cmd(
                'psql -At -p %s -c "%s"' % (inst.db_port, SQL)
            )
        except Exception:
            return None

        return loc


    def get_sync_lag(self, master_xlog):
        """
        For a replica, return how many bytes behind sync is.

        Given an xlog location (presumably obtained from the upstream master)
        we should ask the slave how far it is from that location. Essentially
        this means we're wrapping the pg_xlog_location_diff function and
        using pg_last_xlog_replay_location to calculate the divergence.

        :param master_xlog: Current xlog point as reported by the upstream
               master system.

        :return: Number of bytes of lag, or None.
        """

        inst = self.instance

        if inst.duty != 'slave' or master_xlog is None:
            return None

        try:
            # Never trust user input. Even if we're the user.
            master_xlog = re.sub('[^A-Z/0-9]', '', master_xlog)

            SQL = "SELECT pg_xlog_location_diff('%s', pg_last_xlog_replay_location())" % master_xlog
            bytes_diff = self.__run_cmd(
                'psql -At -p %s -c "%s"' % (inst.db_port, SQL)
            )
        except Exception:
            return None

        return abs(int(bytes_diff))


    def stop(self):
        """
        Stop this PostgreSQL instance

        :raises: Exception if the instance could not be stopped.
        """
        inst = self.instance

        if inst.is_online:
            ver = '.'.join(inst.version.split('.')[:2])
            self.__run_cmd(
                'pg_ctlcluster %s %s stop -m fast' % (ver, inst.instance)
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
            'pg_ctlcluster %s %s reload' % (ver, inst.instance)
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

        self.stop()

        sync = 'rsync -a --rsh=ssh -W --delete'
        sync += ' --exclude=recovery.conf'
        sync += ' --exclude=pg_xlog/*'
        sync += ' --exclude=postmaster.*'
        sync += ' postgres@%s:%s/ %s'

        self.__run_cmd(sync % (
            inst.master.db_host, inst.master.pgdata, inst.pgdata
        ))

        # Handle the pg_xlog data separately so we get all of the upstream
        # changes that might have happened during the transfer. go last. This
        # prevents rsync from complaining about missing files since xlog files
        # rotate frequently.

        sync = 'rsync -a --rsh=ssh -W --delete'
        sync += ' postgres@%s:%s/pg_xlog %s'

        self.__run_cmd(sync % (
            inst.master.db_host, inst.master.pgdata, inst.pgdata
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
            'pg_ctlcluster %s %s promote' % (ver, inst.instance)
        )

        inst.duty = 'master'
        inst.master = None
        inst.save()


    def change_master(self, master):
        """
        Assign a new upstream master to this instance

        Master assignment in this context means two things:
        
        1. A new recovery.conf is written with streaming connection info.
        2. A configuration reload is issued.

        The assumption is that the master and slave are already compatible or
        newly synchronized. If this is not the case, this instance will be
        stopped for manual intervention. The caller is welcome to invoke
        master_sync to ensure the master reassignment is enforced, but we
        don't recommend this approach as a single operation.

        :param master: Django DBInstance model of upstream master to assign.

        :raises: Exception if the instance could not be promoted.
        """

        inst = self.instance
        ver = '.'.join(inst.version.split('.')[:2])

        # Write out a local recovery.conf we can transmit to the instance.
        # Doing it this way is a lot easier than trying to escape everything
        # and sending it via SSH commands.

        rec_file = tempfile.NamedTemporaryFile(bufsize=0)
        rec_path = os.path.join(inst.pgdata, 'recovery.conf')

        info = 'user=%s host=%s port=%s application_name=%s' % (
            'replication', master.db_host, master.db_port,
            inst.db_host + '_' + inst.instance
        )

        rec_file.write("standby_mode = 'on'\n")
        rec_file.write("primary_conninfo = '%s'\n" % info)
        self.receive_file(rec_file.name, rec_path)
        rec_file.close()

        # Reload the config. This should cause the slave to follow the new
        # master. This should have some kind of more advanced check, because
        # the pg_ctlcluster command probably won't exit with an error here.
        # For now, we'll just assume it worked.

        self.reload()

        # Even if this was a master host at one point, it's a replica now.
        # Make sure we record the new master and set the slave attribute.

        inst.duty = 'slave'
        inst.master = master
        inst.save()
