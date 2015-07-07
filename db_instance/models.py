from django.db import models
from django.conf import settings

db_settings=settings.DATABASES['default']

# Create your models here.

class DBInstance(models.Model):
    """
    Define a DB Instance model

    This model defines a table that will store a list of all known PG
    environments. This list will be used in the admin to send commands
    to all systems defined in the admin, or a subset based on search
    parameters.

    Database hosts must be labeled, and may exist in one of three
    environments: dev, stage, or prod. Otherwise, all fields are based on
    database connection parameters. As always, a created and modified date
    column is added for auditing purposes.
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

    instance_id = models.IntegerField(primary_key=True, editable=False)
    instance = models.CharField('Instance Name', max_length=40)

    db_host = models.CharField('DB Host', max_length=40)
    db_port = models.IntegerField('DB Port', max_length=5, default=db_settings['PORT'])
    db_user = models.CharField('DB User', max_length=40, default=db_settings['USER'])
    version = models.CharField('PG Version', max_length=10, default=db_settings['PORT'], blank=True)
    duty = models.CharField('Role', max_length=6, choices=DUTIES, default='master')
    is_online = models.BooleanField('Online', editable=False)
    pgdata = models.CharField('DB Path', max_length=200)
    master_host = models.CharField('Master Host', max_length=40, blank=True)
    master_port = models.IntegerField('Master Port', max_length=5, blank=True)
    environment = models.CharField('Environment', max_length=10, choices=ENVIRONMENTS)

    created_dt = models.DateField()
    modified_dt = models.DateField()

    class Meta:
        verbose_name = 'Database Instance'
        db_table = 'util_instance'

    def __unicode__(self):
        return self.db_host
