What is ElepHaaS
================

ElepHaaS is a Django application written specifically to administer large constellations of PostgreSQL instances distributed across several physical servers. Features include:

* Several view & filter options to focus on specific groups.
* Start or stop any managed instance.
* Replication: promote, synchronize, and remaster.
* Invoke Disaster Recovery failover---including DNS.


Installation Instructions
=========================

Required Python modules:

* dnspython
* django
* django-auth-ldap
* paramiko
* psycopg2

After installing the necessary parts:

* Rename local_settings.example.py to local_settings.py
* Create new secret key, ldap password, etc.
* As postgres user, install the database elements:

 ```bash
 cd /opt/elephaas
 python manage.py syncdb
 ```


Usage Instructions
==================

The packaged version is distributed with a standard init script that can start or stop ElepHaaS as a standalone Django application on port 8000. If using a proxy through another webserver software, feel free to change this port.

In all other cases, redirect a browser to the following URL:

http://host:8000/admin

If the `/admin` path is omitted, the browser will be redirected to the expected location. However, if bookmarking the full admin path, use the post-redirect URL.



