from django.db import models

class Environment(models.Model):
    """
    Define a DB Environment model

    This model defines a table that will store a list of all known server
    environments. Things like dev, QA, UAT, production, etc.
    """

    environment_id = models.AutoField(primary_key=True)
    env_name = models.CharField('Environment Name',
        help_text='Example: dev, stage, prod.',
        max_length=40)
    env_descr = models.TextField('Long Description', max_length=2000,
        help_text='Enter a longer description including use cases or ' +
            'important notes.'
        )
    created_dt = models.DateField()
    modified_dt = models.DateField()

    class Meta:
        verbose_name = 'System Environment'
        db_table = 'ele_environment'
        ordering = ['env_name',]

    def __unicode__(self):
        return self.env_name


class Herd(models.Model):
    """
    Define a Postgres Database Herd

    A database herd is basically a postgres cluster. In our case, it's allowed
    to "stampede" anywhere, so the herd itself has some basic attributes that
    should be shared on any server that hosts it. This model defines those
    shared attributes.
    """

    herd_id = models.AutoField(primary_key=True)
    environment = models.ForeignKey('Environment', on_delete = models.SET_NULL, null=True)
    herd_name = models.CharField('Herd Name', max_length=40,
        help_text='Used to identify this herd, and for CLI tools like pg_ctlcluster.')
    herd_descr = models.TextField('Long Description', max_length=2000,
        help_text='Enter important details, notes, or caveats here.')
    db_port = models.IntegerField('Port',
        help_text='Connection port for hosting this herd. Used for all hosts.')
    pgdata = models.CharField('Data Root', max_length=100,
        help_text='Full path to root data directory. Used for all hosts.')
    vhost = models.CharField('Virtual Host', max_length=40,
        help_text='Virtual host name to identify primary herd member.')
    created_dt = models.DateField()
    modified_dt = models.DateField()

    class Meta:
        verbose_name = 'Herd'
        db_table = 'ele_herd'
        ordering = ['herd_name',]

    def __unicode__(self):
        return self.herd_name


class Server(models.Model):
    """
    Define a Postgres Database Server

    Since we're trying to abstract servers away from the process, this menu
    mainly allows the server to exist as a medium. We want to encourage
    distributing a public SSH key to let the tool simply seize control.
    """

    server_id = models.AutoField(primary_key=True)
    environment = models.ForeignKey('Environment', on_delete = models.SET_NULL, null=True)
    hostname = models.CharField('Host Name', max_length=40)
    created_dt = models.DateField()
    modified_dt = models.DateField()

    class Meta:
        verbose_name = 'Server'
        db_table = 'ele_server'
        ordering = ['hostname',]

    def __unicode__(self):
        return self.hostname

