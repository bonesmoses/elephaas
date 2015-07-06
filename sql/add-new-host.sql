/**
* Functions necessary in hosts managed with pg_admin
*
* These functions provide an API for the pg_admin Django utility. Because
* they run with superuser privileges, they can not be installed by the project
* itself during initialization. Before adding a Database Host in the admin
* page, make sure to run this SQL on that database as a database superuser
* if these functions don't already exist.
*
* Date $Date: 2014-04-08 $
* @author Shaun Thomas <sthomas@optionshouse.com>
* @version: $Revision$
* @package: pg_admin
*/

BEGIN;

SET search_path TO pg_admin;

--------------------------------------------------------------------------------
-- CREATE PROCEDURES
--------------------------------------------------------------------------------

/**
* Create a new PG user, or modify an existing one.
*
* Since neither ALTER USER or CREATE USER are standard insert/update/delete
* procedures, this function acts as a wrapper so specifically elevated users
* can add database users. This is primarily for our Django application.
*
* Users created or modified by this function will have only be valid for a
* period of three months. The assumption is that this function will be
* restricted to managing employee-driven users. This may be changed as the
* API use is expanded.
*
* @param username  Username to create.
* @param password  Plain-text password to assign to the user.
*
* @return boolean status of user creation success.
*/
CREATE OR REPLACE FUNCTION spc_add_database_user(
  username VARCHAR,
  password VARCHAR
)
RETURNS BOOLEAN AS
$BODY$
DECLARE
  super    BOOLEAN := FALSE;
  expires  DATE := CURRENT_DATE + INTERVAL '3 months';
BEGIN
  SELECT usesuper INTO super
    FROM pg_user
   WHERE usename = username;

  -- If this is a superuser, no changes are allowed.

  IF super THEN
    RETURN FALSE;
  END IF;

  IF FOUND THEN
    EXECUTE 'ALTER USER ' || quote_ident(username) || 
            ' WITH PASSWORD ' || quote_literal(password) ||
            ' VALID UNTIL ' || quote_literal(expires);
  ELSE
    EXECUTE 'CREATE USER ' || quote_ident(username) || 
            '  WITH PASSWORD ' || quote_literal(password) ||
            ' VALID UNTIL ' || quote_literal(expires);
  END IF;

  RETURN TRUE;
EXCEPTION
  WHEN OTHERS THEN
    RETURN FALSE;
END;
$BODY$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;


/**
* Drop a specified database user.
*
* Since DROP USER is not a standard insert/update/delete procedure, this
* function acts as a wrapper so specifically elevated users can drop
* known users. This is primarily for our Django application.
*
* Certain safeguards are in place so superusers can not be removed with this
* function.
*
* @param username  Database user to remove.
*
* @return boolean status of user removal success.
*/
CREATE OR REPLACE FUNCTION spc_drop_database_user(
  username VARCHAR
)
RETURNS BOOLEAN AS
$BODY$
BEGIN
  -- Do not drop superusers! Ever!

  PERFORM 1
     FROM pg_user
    WHERE usename = username
      AND usesuper;

  IF FOUND THEN
    RETURN FALSE;
  END IF;

  -- Try to drop the user. We don't have CASCADE enabled, so this could fail
  -- if there are any dependencies on this user.

  EXECUTE 'DROP USER ' || quote_ident(username);
  RETURN TRUE;

EXCEPTION
  WHEN OTHERS THEN
    RETURN FALSE;
END;
$BODY$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;


/**
* Check an PG password hash against the passed value.
*
* The current PG password hashing algorithm follows these rules:
*   algo || algo(password + username)
* where algo is currently md5.
*
* If we calculate this value, we can compare it to the stored hash without
* knowing the current password.
*
* @param username  Username of password to check
* @param password  Plain-text password to hash and compare.
*
* @return boolean status of password check success.
*/
CREATE OR REPLACE FUNCTION spc_check_database_password(
  username VARCHAR,
  password VARCHAR
)
RETURNS BOOLEAN AS
$BODY$
BEGIN

  PERFORM 1
     FROM pg_shadow
    WHERE usename = username
      AND passwd = 'md5' || md5(password || username);

  IF FOUND THEN
    RETURN TRUE;
  END IF;

  RETURN FALSE;

END;
$BODY$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;


--------------------------------------------------------------------------------
-- GRANT ACCESS
--------------------------------------------------------------------------------

REVOKE ALL ON FUNCTION spc_add_database_user(VARCHAR, VARCHAR)
  FROM PUBLIC; 

REVOKE ALL ON FUNCTION spc_drop_database_user(VARCHAR)
  FROM PUBLIC;

REVOKE ALL ON FUNCTION spc_check_database_password(VARCHAR, VARCHAR)
  FROM PUBLIC;

GRANT EXECUTE ON FUNCTION spc_add_database_user(VARCHAR, VARCHAR)
   TO pg_admin;

GRANT EXECUTE ON FUNCTION spc_drop_database_user(VARCHAR)
   TO pg_admin;

GRANT EXECUTE ON FUNCTION spc_check_database_password(VARCHAR, VARCHAR)
   TO pg_admin;

COMMIT; 

--------------------------------------------------------------------------------
