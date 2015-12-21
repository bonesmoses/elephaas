from django.db import models
from django.conf import settings

db_settings=settings.DATABASES['default']

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


class SysAppModel(models.Model):
    class Meta:
        app_label = 'Elephant Herd as a Service'
        abstract = True


class Environment(SysAppModel):
    """
    Define a DB Environment model

    This model defines a table that will store a list of all known server
    environments. Things like dev, QA, UAT, production, etc.
    """

    environment_id = models.AutoField(primary_key=True)
    env_name = models.CharField('Environment Name', max_length=40)
    env_descr = models.TextField('Long Description', max_length=2000)
    created_dt = models.DateField()
    modified_dt = models.DateField()

    class Meta:
        verbose_name = 'System Environment'
        db_table = 'ele_environment'
        ordering = ['env_name',]

    def __unicode__(self):
        return self.env_name

