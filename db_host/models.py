from django.db import models
from django.conf import settings

db_settings=settings.DATABASES['default']

# Create your models here.

class DBHost(models.Model):
    """
    Define a DB Host model

    This model defines a table that will store a list of all known EDB
    environments. This list will be used in the admin to send commands
    to all systems defined in the admin, or a subset based on search
    parameters.

    Database hosts must be labeled, and may exist in one of three
    environments: dev, stage, or prod. Otherwise, all fields are based on
    database connection parameters. As always, a created and modified date
    column is added for auditing purposes.
    """

    ENVIRONMENTS = (
        ('prod', 'Production'),
        ('stage', 'Stage'),
        ('dev', 'Development'),
    )

    db_label = models.CharField('Instance Name', max_length=32)
    db_host = models.CharField('Database Host', max_length=32)
    db_env = models.CharField('Environment', max_length=20, choices=ENVIRONMENTS)
    db_port = models.CharField('Database Port', max_length=32, default=db_settings['PORT'])
    db_user = models.CharField('Database User', max_length=32, default=db_settings['USER'])
    db_name = models.CharField('Database Name', max_length=32, default=db_settings['NAME'])
    created_dt = models.DateField()
    modified_dt = models.DateField()

    class Meta:
        verbose_name = 'Database Host'
        db_table = 'pgdb_host'

    def __unicode__(self):
        return self.db_host
