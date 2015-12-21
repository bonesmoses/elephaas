from django.db import models
from django.conf import settings

db_settings=settings.DATABASES['default']

admin_name = 'Foo'

# Django doesn't have a method for setting the verbose application name
# so we cheat a bit here by overriding the title() method it uses to
# describe the application. It's hacky, but works for now.

class string_with_title(str):
    def __new__(cls, value, title):
        instance = str.__new__(cls, value)
        instance._title = title
        return instance

    def title(self):
        return self._title

    __copy__ = lambda self: self
    __deepcopy__ = lambda self, memodict: self


class DBInstance(models.Model):
    """
    Define a DB Instance model

    This model defines a table that will store a list of all known PG
    environments. This list will be used in the admin to send commands
    to all systems defined in the admin, or a subset based on search
    parameters.
    """

    ENVIRONMENTS = (
        ('prod', 'Prod'),
        ('qa', 'QA'),
        ('uat', 'UAT'),
        ('dev', 'Dev'),
    )

    DUTIES = (
        ('master', 'Master'),
        ('slave', 'Slave'),
    )

    instance_id = models.AutoField(primary_key=True)
    instance = models.CharField('Instance Name', max_length=40)
    environment = models.CharField('Environment', max_length=10, choices=ENVIRONMENTS)

    db_host = models.CharField('DB Host', max_length=40)
    db_port = models.IntegerField('DB Port', default=db_settings['PORT'])
    db_user = models.CharField('DB User', max_length=40, default=db_settings['USER'])
    version = models.CharField('PG Version', max_length=10, default=db_settings['PORT'], blank=True)
    pgdata = models.CharField('DB Path', max_length=200)

    is_online = models.BooleanField('Online', editable=False, default=False)

    duty = models.CharField('Role', max_length=6, choices=DUTIES, default='master')
    master = models.ForeignKey('self', on_delete = models.SET_NULL, blank=True, null=True)

    created_dt = models.DateField()
    modified_dt = models.DateField()

    class Meta:
        app_label = string_with_title('db_instance', 'Instance Management')
        verbose_name = 'Database Instance'
        db_table = 'util_instance'
        ordering = ['db_host', 'instance']

    def __unicode__(self):
        return self.db_host + ' - ' + self.instance


class DBReplica(DBInstance):
    class Meta:
        app_label = DBInstance._meta.app_label
        proxy = True
        verbose_name = 'Replica'


class DBDR(models.Model):
    """
    Define a DB Disaster Recovery model

    
    """

    drpair_id = models.AutoField(primary_key=True)
    label = models.CharField('Label', max_length=40)
    primary = models.ForeignKey('DBInstance', related_name = '+')
    secondary = models.ForeignKey('DBInstance', related_name = '+')
    vhost = models.CharField('Virtual Host', max_length=40)
    in_sync = models.BooleanField('In Sync', default=False)

    created_dt = models.DateField()
    modified_dt = models.DateField()

    class Meta:
        app_label = string_with_title('db_instance', 'Instance Management')
        verbose_name = 'Disaster Recovery Pair'
        db_table = 'util_drpair'

    def __unicode__(self):
        return self.label


