from db_host.models import DBHost
import psycopg2

class Control():

    def connect(self, db_host):
        return psycopg2.connect(
            host = db_host.db_host, port = db_host.db_port,
            database = db_host.db_name, user = db_host.db_user
        )

    def save(self, username, password):
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

    def delete(self, username):
        for db_host in DBHost.objects.all():
            try:
                conn = self.connect(db_host)
                cur = conn.cursor()
                cur.execute("SELECT spc_drop_database_user(%s)", (username,))
                conn.commit()
            except:
                pass

