from django.db import models, connection
from db_user.control import Control

# Create your models here.

class DBUser(models.Model):
    """
    A glorified wrapper for the pg_user EDB system view.
    
    This class acts as a universal change broadcasting and detection system.
    One "master" database acts as a source of all user definitions, while
    several external systems can be modified simultaneously.

    We only need minimal information from pg_user view. Every other field is
    only available for Django compatibility and availability of certain
    administration features.
    """

    usesysid = models.IntegerField(primary_key=True, editable=False)
    usesuper = models.BooleanField(editable=False)
    usename = models.CharField('Username', max_length=32)
    passwd = models.CharField('Password', max_length=32)

    class Meta:
        verbose_name = 'DB User'
        db_table = 'pg_user'
        managed = False

    def save(self, *args, **kwargs):
        """
        Save user changes to all database hosts.
        
        We use an external control library here because we're broadcasting
        the change to all database hosts defined in the db_instance app.
        """
        ctl = Control()
        ctl.save(self.usename, self.passwd)


    def delete(self, *args, **kwargs):
        """
        Delete a user from all database hosts.
        
        We use an external control library here because we're broadcasting
        the change to all database hosts defined in the db_instance app.
        """
        ctl = Control()
        ctl.delete(self.usename)


    def check_password(self, password):
        """
        Check a user-submitted password against the stored EDB hash.

        For this function to work properly, the spc_check_database_password
        procedure must be defined on the EDB instance this app is using as
        a base.

        :param password: Password value to check against the user currently
            loaded into the model.
        """
        cur = connection.cursor()
        val = cur.execute(
            "SELECT spc_check_database_password(%s, %s)",
            (self.usename, password)
        )
        row = cur.fetchone()
        return row[0]


    def __unicode__(self):
        return self.usename
