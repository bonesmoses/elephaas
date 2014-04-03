from django.db import models

# Create your models here.


class DBHost(models.Model):
    ENVIRONMENTS = (
        ('prod', 'Production'),
        ('stage', 'Stage'),
        ('dev', 'Development'),
    )

    db_label = models.CharField('Instance Name', max_length=32)
    db_host = models.CharField('Database Host', max_length=32)
    db_env = models.CharField('Environment', max_length=20, choices=ENVIRONMENTS)
    db_port = models.CharField('Database Port', max_length=32, default="5444")
    db_user = models.CharField('Database User', max_length=32, default="enterprisedb")
    db_name = models.CharField('Database Name', max_length=32)
    created_dt = models.DateField()
    modified_dt = models.DateField()

    class Meta:
        verbose_name = 'Database Host'
        db_table = 'pgdb_host'

    def __unicode__(self):
        return self.db_host
