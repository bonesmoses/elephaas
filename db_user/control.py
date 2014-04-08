from db_host.models import DBHost
import psycopg2

class Control():
    """
    Provide a basic Python API for manipulating EDB users via Django

    This class exists primarily to "wrap" user administration. This wrapper
    is necessary because the API is broadcasted to several EDB systems
    simultaneously.

    API calls themselves are declared with SECURITY DEFINER, so they run
    as the superuser that created them. This allows API calls to perform
    admin-level tasks without potentially causing database problems.
    """


    def connect(self, db_host):
        """
        Return an EDB connection for a specified DBHost model

        Unlike most Django pieces, this directly calls out to psycopg. This
        class isn't meant to be abstract, and this tool is built for EDB.
        See psycopg documentation on how to interact with the returned 
        connection object.

        :param db_host: A DBHost Django model object containing connection
            information.

        :rtype: psycopg2 connection object
        """
        return psycopg2.connect(
            host = db_host.db_host, port = db_host.db_port,
            database = db_host.db_name, user = db_host.db_user
        )


    def delete(self, username):
        """
        Delete a user to all registered EDB hosts

        Assuming the DBHost model is configured with a list of defined
        EDB hosts, connect to each and call the spc_drop_database_user
        procedure to remove the named user.

        :param username: EDB username to delete.
        """
        for db_host in DBHost.objects.all():
            try:
                conn = self.connect(db_host)
                cur = conn.cursor()
                cur.execute("SELECT spc_drop_database_user(%s)", (username,))
                conn.commit()
            except:
                pass


    def save(self, username, password):
        """
        Save a new or modified user to all registered EDB hosts

        Assuming the DBHost model is configured with a list of defined 
        EDB hosts, connect to each and call the spc_add_database_user
        procedure to create a new user, or change an existing one.

        :param username: EDB username to create or modify.
        :param password: Password for the above user. If the user already
            exists, this will be their new password.
        """
        for db_host in DBHost.objects.all():
            try:
                conn = self.connect(db_host)
                cur = conn.cursor()
                cur.execute("SELECT spc_add_database_user(%s, %s)", 
                    (username, password)
                )
                conn.commit()
            except:
                raise
