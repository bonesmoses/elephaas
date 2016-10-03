What is ElepHaaS
================

ElepHaaS is a Django application written specifically to administer large constellations of PostgreSQL instances distributed across several physical servers. Features include:

* Several view & filter options to focus on specific groups.
* Start, stop, restart, or reload any managed instance.
* Replication: promote, synchronize, and remaster.
* Invoke Disaster Recovery failover---including DNS.


Installation Instructions
=========================

ElepHaaS is a Django application. As such, it can basically run from anywhere. However, we still need several Python prerequisites.


Required Modules
----------------

Since ElepHaaS uses Django, several supporting Python modules are also necessary to get everything working. Let's cover the basics:

* django (The engine for this little buggy)
* psycopg2 (For Postgres!)
* dnspython (For DNS and disaster recovery management)
* paramiko (For executing remote SSH commands on hosts.)


Optional Modules
----------------

Optionally, some modules can be included for enhanced or extended functionality.

* django-auth-ldap (For larger organizations with unified login systems.)


Debian Based Systems
--------------------

To install on any Debian, Ubuntu, Mint, or otherwise `.deb` package system, it's fairly easy to gather all of the elements.

```bash
sudo apt-get install python-dnspython python-django python-psycopg2 \
     python-paramiko
sudo apt-get install python-django-auth-ldap # Optional
```

Then, just install the ElepHaaS package:

```bash
sudo dpkg -i elephaas_1.0.0-1_all.deb
```

Afterwards, all relevant files will be located in `/opt/elephaas`.


Linux/UNIX Systems
------------------

We recommend using [pip](https://pypi.python.org/pypi/pip) to install required Python elements:

```bash
pip install django psycopg2 paramiko dnspython
pip install django-auth-ldap # Optional
```

Since ElepHaaS acts as a service, we recommend placing it in `/opt` or some other easily-isolated location. We've also included a very basic `init.d` style script for starting and stopping the service itself.

```bash
sudo tar -C /opt -xzf elephaas-1.0.0.tar.gz
sudo ln -s /opt/elephaas-1.0.0 /opt/elephaas
sudo cp /opt/elephaas/debian/elephaas.init /etc/init.d/elephaas
sudo chmod 755 /etc/init.d/elephaas
```

ElepHaaS also uses SSH key authentication for executing commands on remote systems. This is the core to how it controls all of those Postgres instances. If you don't have one yet for the user that will be running the ElepHaaS service, generate a new set:

```bash
mkdir -m 0700 ~/.ssh
ssh-keygen -t rsa
cat ~/.ssh/id_rsa.pub
```

We want the output of the `.ssh/id_rsa.pub` file to configure ElepHaaS itself. Some menus will display this key to remind users that upstream servers need this value in their `.ssh/authorized_keys` file in order for it to manage them.


Configuration
-------------

Since ElepHaaS is a Django project, configuration is done by modifying the standard `elephaas/local_settings.py` file. To get your ElepHaaS installation in running condition, follow these steps:

* Rename `local_settings.example.py` to `local_settings.py`
* Modify `local_settings.py` and fill in the secret key, public key, Postgres connection settings, etc.
* Install the database elements. By default, ElepHaaS runs in the `utility` schema within the `admin` database. Both of these will need to exist prior to finishing the installation. An easy way to do this is to run these commands as the `postgres` user:

 ```bash
 createdb admin
 psql admin -c 'CREATE SCHEMA utility;'
 cd /opt/elephaas
 python manage.py migrate
 ```
* Finally, if not using the optional LDAP authentication module, we'll need to create a basic superuser to manage ElepHaaS admins. Create one with `manage.py`:

 ```bash
 cd /opt/elephaas
 python manage.py createsuperuser
 ```


Running ElepHaaS
================

The Debian packaged version is distributed with a standard init script that can start or stop ElepHaaS as a standalone Django application on port 8000. If you'd rather not use this method, ElepHaaS runs the same way as any other Django app. An easy way to launch is to use the `runserver` primitive:

```bash
cd /opt/elephaas
python manage.py runserver 0.0.0.0:8000 &> /path/to/log.file &
```

Running the server this way isn't generally recommended for obvious reasons. We strongly encourage scripting the process in some manner to avoid relying on ad-hoc launching if possible.


Usage Instructions
==================

Once ElepHaaS is running (default is port 8000), redirect a browser to the following URL:

http://host:8000/admin

If the `/admin` path is omitted, the browser will be redirected to the expected location. However, if bookmarking the full admin path, use the post-redirect URL.


Extended Configuration
======================

Several more settings are available in `elephaas/local_settings.py` that may require modification depending on server environment. Please refer to this section for further information.

Commands
--------

Since ElepHaaS was written primarily within an Ubuntu distribution, some of the defaults remote administrative commands may not operate normally on other operating systems. To correct this, change the `COMMANDS` dictionary settings as described below.

| Setting | Description |
|---------|-------------|
| base | Optional root command used as a template for all other commands. To use this in another command definition, use {COMMANDS[base]}. |
| start | Command necessary to start a Postgres instance. By default, this uses `pg_ctlcluster` for Debian / Ubuntu systems. |
| stop | Command necessary to stop a Postgres instance. By default, this uses `pg_ctlcluster` for Debian / Ubuntu systems. |
| reload | Command necessary to reload a Postgres instance so it rereads configuration files. By default, this uses `pg_ctlcluster` for Debian / Ubuntu systems. |
| promote | Command necessary to promote a Postgres instance to a fully online read/write state. By default, this uses `pg_ctlcluster` for Debian / Ubuntu systems. |
| init | Command necessary to initialize a new Postgres instance. By default, this uses `pg_initcluster` for Debian / Ubuntu systems. |

In addition to these dictionary definitions, there are also some variables available for use within the definitions themselves.

| Value | Notes |
|-------|-------|
| pgdata | Full path to the primary data directory for a Postgres instance. Since this is defined for the herd or overridden within the instance itself, this value is the most specific of the two. If an instance override is provided, it will be used instead of the herd default. |
| version | A multiple element array for the major, minor, and (potentially) bugfix elements of the Postgres instance version. In many cases, this value is obtained from `PG_VERSION` within the instance data directory. As such, it's safest to use only the first two elements: {version[0]}, and {version[1]}. |
| inst | The instance object itself. Standard python dot notation can drill down the entire instance attribute tree. |

Example
-------

In a system that intends to use `pg_ctl` and `pg_init` instead of Debian or Ubuntu wrappers, and has multiple Postgres versions installed, the `COMMANDS` dictionary might resemble something like this:

```python
COMMANDS = {
    'base': '/usr/pgsql-{version[0]}.{version[1]}/bin/pg_ctl -D {pgdata}',
    'start': '{COMMANDS[base]} start',
    'stop': '{COMMANDS[base]} stop -m fast',
    'reload': '{COMMANDS[base]} reload',
    'promote': '{COMMANDS[base]} promote',
    'init': '/usr/pgsql-{version[0]}.{version[1]}/bin/pg_init -D {pgdata} -p {inst.herd.db_port}',
}
```

Notes
=====

ElepHaaS assumes the `postgres` OS user has read/write access to all remote instances. All SSH commands on remote systems will use this user as well. This means the `~/.ssh/authorized_keys` file and all associated files should reside within the home of the `postgres` user as well. There is a TODO item to make this configurable.

Though these elements are listed in the `TODO` file, they are currently important limitations of ElepHaaS and should be listed upfront. Please keep this in mind when trying to utilize its functionality.

Some menus also list an 'MB Lag' column. This is a calculated value based on the contents of the `xlog_pos` column in the `ele_instance` table. To keep these values up to date without relying on an ad-hoc reporting system, please install [ele_tools](https://github.com/peak6/ele_tools) on managed Postgres systems. It will autodetect instances and report online status as well as `xlog_pos` and other information so ElepHaaS always has an accurate picture of instance status.

